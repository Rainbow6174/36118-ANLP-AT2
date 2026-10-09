"""POST /api/analyse."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import services
from ..ports.classifier import Classifier
from ..ports.retriever import Retriever
from ..schemas import AnalyseRequest, AnalyseResponse, Prediction

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
    prediction = Prediction.model_validate(classifier.classify(payload.text))
    related = retriever.retrieve(
        payload.text,
        k=5,
        filters={"board_label": prediction.predicted_label},
    )
    return AnalyseResponse(
        prediction=prediction,
        related_reports=related,
        extraction=None,
    )
