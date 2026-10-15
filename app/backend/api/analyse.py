"""POST /api/analyse."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from .. import services
from ..ports.classifier import Classifier
from ..ports.retriever import Retriever
from ..schemas import AnalyseRequest, AnalyseResponse, Prediction

logger = logging.getLogger(__name__)

router = APIRouter()

def get_classifier() -> Classifier:
    return services.get_classifier()


def get_retriever() -> Retriever:
    return services.get_retriever()


@router.post("/analyse", response_model=AnalyseResponse)
def analyse(
    payload: AnalyseRequest,
    classifier: Classifier = Depends(get_classifier),
    retriever: Retriever = Depends(get_retriever),
) -> AnalyseResponse:
    try:
        prediction = Prediction.model_validate(classifier.classify(payload.text))
    except Exception as exc:
        logger.exception("Classification failed for input of length %d", len(payload.text))
        raise HTTPException(status_code=503, detail="Classification service unavailable") from exc
    try:
        related = services.find_related(retriever, payload.text, k=5)
    except Exception:
        logger.exception("Retrieval failed, returning prediction without related reports")
        related = []
    return AnalyseResponse(
        prediction=prediction,
        related_reports=related,
        extraction=None,
    )
