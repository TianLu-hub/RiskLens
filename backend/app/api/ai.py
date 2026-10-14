"""AI Risk Officer API route."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.ai.officer import (
    AIConfigurationError,
    AIProviderError,
    RiskOfficerAI,
    answer_risk_question,
    get_risk_officer_ai,
)
from app.ai.scenario_parser import ScenarioInterpretationError
from app.models.ai import RiskOfficerRequest, RiskOfficerResponse

router = APIRouter(prefix="/ai", tags=["AI Risk Officer"])


def get_configured_risk_officer_ai() -> RiskOfficerAI:
    """Translate missing backend configuration into a stable API response."""

    try:
        return get_risk_officer_ai()
    except AIConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "AI_NOT_CONFIGURED", "message": str(error)},
        ) from error


@router.post("/risk-officer", response_model=RiskOfficerResponse)
def risk_officer(
    payload: RiskOfficerRequest,
    provider: Annotated[RiskOfficerAI, Depends(get_configured_risk_officer_ai)],
) -> RiskOfficerResponse:
    """Interpret intent and explain only backend-calculated quantitative results."""

    try:
        return answer_risk_question(payload, provider)
    except ScenarioInterpretationError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_AI_SCENARIO", "message": str(error)},
        ) from error
    except AIProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": error.code,
                "message": error.public_message,
                "stage": error.stage,
            },
        ) from error
