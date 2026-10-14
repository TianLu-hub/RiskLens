"""Input and output contracts for historical portfolio optimization."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.models.portfolio import AnalyzeRequest
from app.models.responses import DataQuality

OptimizationObjective = Literal["minimum_volatility", "maximum_sharpe", "risk_parity"]


class OptimizeRequest(AnalyzeRequest):
    """Optimize the supplied long-only holdings without changing them."""

    objective: OptimizationObjective = "minimum_volatility"
    max_position_weight: float | None = Field(default=None, gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_position_cap(self) -> Self:
        if (
            self.max_position_weight is not None
            and len(self.positions) * self.max_position_weight < 1.0 - 1e-10
        ):
            raise ValueError(
                "Max position weight is infeasible for the number of assets"
            )
        return self


class OptimizationMetrics(BaseModel):
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float | None
    hhi: float
    effective_positions: float


class AllocationComparison(BaseModel):
    ticker: str
    current_weight: float
    optimized_weight: float
    weight_change: float


class OptimizationResponse(BaseModel):
    objective: OptimizationObjective
    max_position_weight: float | None
    current: OptimizationMetrics
    optimized: OptimizationMetrics
    allocations: list[AllocationComparison]
    one_way_turnover: float
    data_quality: DataQuality
    methodology: str
    limitations: list[str]
