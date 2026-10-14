"""Load and connect the selected classifier and retrieval implementation.

The existing member-owned paths stay unchanged:

- the deployment model is read from ``models/transformer/``;
- the retrieval index is read from ``models/retrieval/index/``;
- the API remains in ``app/backend/``.

``CRISISLENS_RUNTIME`` controls startup:

- ``real`` requires both real components and fails clearly when an artefact is
  missing;
- ``mock`` keeps the lightweight development and test behaviour;
- ``auto`` (the repository default) uses the real components when all local
  artefacts exist, otherwise it starts with mocks and reports why in /api/health.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import store
from .ports.classifier import Classifier, MockClassifier
from .ports.retriever import MockRetriever, Retriever
from .schemas import Prediction, RelatedReport, ReportRecord

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _REPO_ROOT / "app" / "app_models.json"

_classifier: Classifier = MockClassifier()
_retriever: Retriever = MockRetriever()
_status: dict[str, Any] = {
    "requested_runtime": "auto",
    "active_runtime": "mock",
    "classifier": "mock-v0",
    "retriever": "mock",
    "detail": "Services have not been initialised yet.",
}


class TransformerClassifierAdapter:
    """Validate Member 3's dictionary response against the API contract."""

    def __init__(self, model: Any):
        self._model = model
        self.model_version = model.model_version

    def classify(self, text: str) -> Prediction:
        return Prediction.model_validate(self._model.classify(text))


class RetrievalAdapter:
    """Expose Member 5's module functions through Member 4's object port."""

    name = "member5-semantic-retrieve-tfidf-search"

    def __init__(self, module: Any):
        self._module = module

    @staticmethod
    def _validated(items: list[dict]) -> list[RelatedReport]:
        return [RelatedReport.model_validate(item) for item in items]

    def retrieve(
        self,
        text: str,
        k: int = 5,
        filters: dict | None = None,
        exclude_ids=None,
    ) -> list[RelatedReport]:
        return self._validated(
            self._module.retrieve(
                text,
                k=k,
                filters=filters,
                exclude_ids=exclude_ids,
            )
        )

    def search(
        self,
        query: str,
        filters: dict | None = None,
        k: int = 20,
        exclude_ids=None,
    ) -> list[RelatedReport]:
        return self._validated(
            self._module.search(
                query,
                filters=filters,
                k=k,
                exclude_ids=exclude_ids,
            )
        )

    def add_to_index(self, report: ReportRecord | dict) -> None:
        payload = report.model_dump() if isinstance(report, ReportRecord) else report
        self._module.add_to_index(payload)

    def remove_from_index(self, message_id: str) -> bool:
        return self._module.remove_from_index(message_id)

    def warm_up(self) -> None:
        self._module.warm_up()

    def reset(self) -> None:
        self._module.reset_index()


def _read_config() -> dict:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"Model configuration not found: {_CONFIG_PATH}")
    with _CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else _REPO_ROOT / path


def _model_files_ready(model_dir: Path) -> bool:
    required = (
        model_dir / "metadata.json",
        model_dir / "config.json",
        model_dir / "tokenizer_config.json",
    )
    has_weights = (model_dir / "model.safetensors").exists() or (
        model_dir / "pytorch_model.bin"
    ).exists()
    has_tokenizer = (model_dir / "tokenizer.json").exists() or (
        model_dir / "vocab.txt"
    ).exists()
    return all(path.exists() for path in required) and has_weights and has_tokenizer


def _retrieval_files_ready(index_dir: Path) -> bool:
    required = (
        "history.parquet",
        "tfidf_vectorizer.joblib",
        "tfidf_matrix.npz",
        "semantic_embeddings.npy",
        "semantic_info.json",
    )
    return all((index_dir / name).exists() for name in required)


def _load_real(config: dict) -> tuple[Classifier, RetrievalAdapter]:
    model_dir = _repo_path(config["classifier"]["model_dir"])
    index_dir = _repo_path(config["retrieval"]["index_dir"])

    missing: list[str] = []
    if not _model_files_ready(model_dir):
        missing.append(
            f"deployment model files in {model_dir} "
            "(download the m3-transformer-v1 release)"
        )
    if not _retrieval_files_ready(index_dir):
        missing.append(
            f"retrieval index in {index_dir} (run models/retrieval/build_index.py)"
        )
    if missing:
        raise FileNotFoundError("Missing " + " and ".join(missing))

    from models.retrieval import retrieval as retrieval_module
    from models.transformer import load_model

    classifier = TransformerClassifierAdapter(load_model(model_dir=model_dir))
    retriever = RetrievalAdapter(retrieval_module)
    retriever.reset()

    page = 1
    page_size = 500
    while True:
        reports, total = store.list_reports(
            source_type="user", page=page, k=page_size
        )
        for report in reports:
            retriever.add_to_index(report)
        if page * page_size >= total:
            break
        page += 1

    retriever.warm_up()
    return classifier, retriever


def configure() -> None:
    """Configure services once for the current API process."""

    global _classifier, _retriever, _status

    config = _read_config()
    requested = os.environ.get(
        "CRISISLENS_RUNTIME", config.get("runtime", "auto")
    ).strip().lower()
    if requested not in {"auto", "real", "mock"}:
        raise ValueError("CRISISLENS_RUNTIME must be auto, real or mock")

    if requested == "mock":
        _classifier = MockClassifier()
        _retriever = MockRetriever()
        _status = {
            "requested_runtime": requested,
            "active_runtime": "mock",
            "classifier": _classifier.model_version,
            "retriever": "mock",
            "detail": "Mock runtime was requested explicitly.",
        }
        return

    try:
        _classifier, _retriever = _load_real(config)
    except (FileNotFoundError, ImportError) as exc:
        if requested == "real":
            raise RuntimeError(
                f"Real CrisisLens runtime could not start: {exc}"
            ) from exc
        _classifier = MockClassifier()
        _retriever = MockRetriever()
        _status = {
            "requested_runtime": requested,
            "active_runtime": "mock",
            "classifier": _classifier.model_version,
            "retriever": "mock",
            "detail": str(exc),
        }
        return

    _status = {
        "requested_runtime": requested,
        "active_runtime": "real",
        "classifier": _classifier.model_version,
        "retriever": _retriever.name,
        "detail": "Member 3 classifier and Member 5 retrieval index are ready.",
    }


def get_classifier() -> Classifier:
    return _classifier


def get_retriever() -> Retriever:
    return _retriever


def index_report(report: ReportRecord) -> None:
    """Keep newly saved or corrected user reports searchable immediately."""

    add = getattr(_retriever, "add_to_index", None)
    if add is not None:
        add(report)


def remove_report_from_index(message_id: str) -> None:
    """Stop a deleted user report from appearing in retrieval results."""

    remove = getattr(_retriever, "remove_from_index", None)
    if remove is not None:
        remove(message_id)


def runtime_status() -> dict[str, Any]:
    return dict(_status)
