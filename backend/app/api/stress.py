"""Hypothetical portfolio stress-test routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.stress import StressTestRequest, StressTestResponse
from app.risk.stress_engine import run_stress_test

router = APIRouter(tags=["stress testing"])


@router.post("/portfolio/stress-test", response_model=StressTestResponse)
def stress_test(payload: StressTestRequest) -> StressTestResponse:
    """Run a deterministic, assumption-labeled hypothetical scenario."""

    return run_stress_test(payload)
