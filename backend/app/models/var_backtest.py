"""Contracts for rolling, one-day historical VaR validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.portfolio import AnalyzeRequest
from app.models.responses import DataQuality

KupiecWarningCode = Literal["low_expected_counts", "boundary_breach_count"]


class KupiecTestResult(BaseModel):
    """Asymptotic unconditional-coverage test at a fixed 5% significance level."""

    method: Literal["kupiec_unconditional_coverage"] = "kupiec_unconditional_coverage"
    statistic: float = Field(ge=0.0, allow_inf_nan=False)
    p_value: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    degrees_of_freedom: Literal[1] = 1
    significance_level: Literal[0.05] = 0.05
    reject_null: bool
    null_breach_probability: float = Field(gt=0.0, lt=1.0, allow_inf_nan=False)
    observed_breach_probability: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    observations: int = Field(gt=0)
    breaches: int = Field(ge=0)
    warning_codes: list[KupiecWarningCode] = Field(default_factory=list)


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
    kupiec_test: KupiecTestResult
    series: list[VarBacktestPoint]
    data_quality: DataQuality
    methodology: str
    limitations: list[str]
