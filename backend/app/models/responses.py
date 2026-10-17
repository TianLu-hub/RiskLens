"""Typed response contracts for Phase 1 analytics."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.data.provenance import MarketDataProvenance


class TimeSeriesPoint(BaseModel):
    date: str
    value: float


class RiskMetrics(BaseModel):
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float | None
    var: float
    cvar: float
    confidence_level: float
    var_horizon_days: int = 1
    risk_free_rate: float


class DrawdownResult(BaseModel):
    current_drawdown: float
    max_drawdown: float
    series: list[TimeSeriesPoint]


class CorrelationPair(BaseModel):
    asset_1: str
    asset_2: str
    correlation: float


class CorrelationResult(BaseModel):
    tickers: list[str]
    matrix: list[list[float]]
    highest_correlations: list[CorrelationPair]


class RiskContributionItem(BaseModel):
    ticker: str
    weight: float
    marginal_risk: float
    absolute_risk_contribution: float
    risk_contribution: float


class ConcentrationResult(BaseModel):
    hhi: float
    effective_positions: float
    largest_position: float
    largest_position_ticker: str
    top_3_concentration: float
    position_count: int


class RiskFlag(BaseModel):
    code: str
    severity: str
    title: str
    detail: str


class DataQuality(BaseModel):
    source: str
    observations: int
    start_date: str
    end_date: str
    requested_lookback_years: int
    warnings: list[str] = Field(default_factory=list)
    provenance: MarketDataProvenance | None = None


class FactorExposureResult(BaseModel):
    """Observed regression estimates; unavailable factors remain explicit nulls."""

    model: str = "CAPM_SPY"
    benchmark_ticker: str = "SPY"
    benchmark_source: str | None
    available: bool
    alpha_annualized: float | None
    market_beta: float | None
    smb_beta: float | None = None
    hml_beta: float | None = None
    r_squared: float | None
    idiosyncratic_volatility: float | None
    observations: int
    rolling_window_days: int = 60
    rolling_beta: list[TimeSeriesPoint] = Field(default_factory=list)
    methodology: str = (
        "OLS on aligned daily portfolio and SPY excess returns; the daily intercept "
        "is annualized by 252. Rolling beta uses a trailing 60-trading-day window."
    )
    unavailable_reason: str | None = None


class PortfolioAnalysisResponse(BaseModel):
    metrics: RiskMetrics
    performance: list[TimeSeriesPoint]
    drawdown: DrawdownResult
    correlation: CorrelationResult
    risk_contributions: list[RiskContributionItem]
    concentration: ConcentrationResult
    factor_exposure: FactorExposureResult
    risk_flags: list[RiskFlag]
    data_quality: DataQuality


class HistoryPoint(BaseModel):
    date: str
    adjusted_close: float


class MarketHistoryResponse(BaseModel):
    ticker: str
    source: str
    history: list[HistoryPoint]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
