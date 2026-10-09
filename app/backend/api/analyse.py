"""POST /api/analyse."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..ports.classifier import Classifier, MockClassifier
from ..ports.retriever import MockRetriever, Retriever
from ..schemas import AnalyseRequest, AnalyseResponse

router = APIRouter()

_classifier = MockClassifier()
_retriever = MockRetriever()


def get_classifier() -> Classifier:
    return _classifier


def get_retriever() -> Retriever:
    return _retriever


@router.post("/analyse", response_model=AnalyseResponse)
def analyse(
    payload: AnalyseRequest,
    classifier: Classifier = Depends(get_classifier),
    retriever: Retriever = Depends(get_retriever),
) -> AnalyseResponse:
    prediction = classifier.classify(payload.text)
    related = retriever.retrieve(payload.text, k=5)
    return AnalyseResponse(
        prediction=prediction,
        related_reports=related,
        extraction=None,
    )
