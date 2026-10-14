"""Contracts for chronological, rolling out-of-sample allocation tests."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.optimization import OptimizationObjective, OptimizeRequest
from app.models.responses import DataQuality


class BacktestRequest(OptimizeRequest):
    """Use a trailing training window and a disjoint forward test window."""

    training_days: int = Field(default=504, ge=60, le=1000)
    rebalance_days: int = Field(default=21, ge=5, le=126)
    cost_bps: float = Field(default=10.0, ge=0.0, le=100.0)


class BacktestMetrics(BaseModel):
    cumulative_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float | None
    max_drawdown: float
    final_wealth: float
    total_one_way_turnover: float
    total_cost_fraction_of_initial_capital: float


class BacktestPoint(BaseModel):
    date: str
    current_wealth: float
    optimized_wealth: float
    spy_wealth: float | None


class BacktestFold(BaseModel):
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    optimized_weights: dict[str, float]
    optimized_one_way_turnover: float
    current_one_way_turnover: float


class BacktestResponse(BaseModel):
    objective: OptimizationObjective
    current: BacktestMetrics
    optimized: BacktestMetrics
    spy_buy_and_hold: BacktestMetrics | None
    series: list[BacktestPoint]
    folds: list[BacktestFold]
    data_quality: DataQuality
    training_days: int
    rebalance_days: int
    cost_bps: float
    methodology: str
    limitations: list[str]
