"""Contracts for rolling, one-day historical VaR validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.portfolio import AnalyzeRequest
from app.models.responses import DataQuality


class VarBacktestRequest(AnalyzeRequest):
    """Validate historical VaR; inherited risk_free_rate is intentionally unused."""

    window_days: int = Field(default=252, ge=60, le=1260)


class VarBacktestPoint(BaseModel):
    date: str
    training_start: str
    training_end: str
    var_loss: float
    realized_return: float
    realized_loss: float
    breach: bool


class VarBacktestResponse(BaseModel):
    method: Literal["historical_simulation"] = "historical_simulation"
    confidence_level: float
    window_days: int
    forecast_horizon_days: Literal[1] = 1
    test_observations: int
    breach_count: int
    expected_breach_count: float
    breach_rate: float
    expected_breach_rate: float
    test_start: str
    test_end: str
    series: list[VarBacktestPoint]
    data_quality: DataQuality
    methodology: str
    limitations: list[str]
