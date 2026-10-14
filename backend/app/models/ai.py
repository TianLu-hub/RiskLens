"""Typed contracts for the AI Risk Officer boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.models.portfolio import Position, WEIGHT_TOLERANCE
from app.models.responses import (
    ConcentrationResult,
    CorrelationPair,
    DataQuality,
    FactorExposureResult,
    RiskContributionItem,
    RiskFlag,
    RiskMetrics,
)
from app.models.stress import StressTestResponse


class OfficerIntent(StrEnum):
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    STRESS_SCENARIO = "stress_scenario"


class EvidenceKey(StrEnum):
    ANNUALIZED_RETURN = "annualized_return"
    ANNUALIZED_VOLATILITY = "annualized_volatility"
    SHARPE_RATIO = "sharpe_ratio"
    VAR = "var"
    CVAR = "cvar"
    MAX_DRAWDOWN = "max_drawdown"
    CURRENT_DRAWDOWN = "current_drawdown"
    EFFECTIVE_POSITIONS = "effective_positions"
    LARGEST_POSITION = "largest_position"
    TOP_THREE_CONCENTRATION = "top_three_concentration"
    HIGHEST_CORRELATION = "highest_correlation"
    LARGEST_RISK_CONTRIBUTOR = "largest_risk_contributor"
    RISK_FLAGS = "risk_flags"
    MARKET_BETA = "market_beta"
    FACTOR_ALPHA = "factor_alpha"
    FACTOR_R_SQUARED = "factor_r_squared"
    IDIOSYNCRATIC_VOLATILITY = "idiosyncratic_volatility"
    STRESS_PORTFOLIO_RETURN = "stress_portfolio_return"
    STRESS_DOLLAR_PNL = "stress_dollar_pnl"
    STRESS_TOP_CONTRIBUTOR = "stress_top_contributor"


class ParsedTickerShock(BaseModel):
    ticker: str
    shock: float = Field(ge=-1.0, le=1.0)


class ParsedRiskIntent(BaseModel):
    """Strict LLM output used only to classify and translate user intent."""

    intent: OfficerIntent
    scenario_name: str | None
    market_shock: float | None = Field(ge=-1.0, le=1.0)
    tech_shock: float | None = Field(ge=-1.0, le=1.0)
    rates_shock_bps: float | None = Field(ge=-1_000.0, le=1_000.0)
    ticker_shocks: list[ParsedTickerShock]


class DrawdownSummary(BaseModel):
    current_drawdown: float
    max_drawdown: float


class CorrelationSummary(BaseModel):
    highest_correlations: list[CorrelationPair] = Field(max_length=10)


class RiskOfficerAnalysisContext(BaseModel):
    """Compact calculated context; price histories never enter the LLM boundary."""

    metrics: RiskMetrics
    drawdown: DrawdownSummary
    correlation: CorrelationSummary
    risk_contributions: list[RiskContributionItem] = Field(min_length=1, max_length=50)
    concentration: ConcentrationResult
    factor_exposure: FactorExposureResult
    risk_flags: list[RiskFlag] = Field(max_length=20)
    data_quality: DataQuality


class RiskOfficerRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)
    positions: list[Position] = Field(min_length=1, max_length=50)
    portfolio_value: float | None = Field(default=None, gt=0.0, le=1_000_000_000_000)
    analysis: RiskOfficerAnalysisContext

    @model_validator(mode="after")
    def validate_portfolio(self) -> Self:
        tickers = [position.ticker for position in self.positions]
        if len(tickers) != len(set(tickers)):
            raise ValueError("Each ticker may appear only once")
        total_weight = sum(position.weight for position in self.positions)
        if abs(total_weight - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                f"Portfolio weights must sum to 1.0; received {total_weight:.6f}"
            )
        return self


# Numeric characters and currency/percentage symbols are excluded from LLM-authored
# prose. Quantitative evidence is injected later from deterministic Python results.
QualitativeText = Annotated[
    str,
    Field(min_length=1, max_length=800, pattern=r"^[^0-9%$]*$"),
]


class OfficerFindingDraft(BaseModel):
    title: QualitativeText
    explanation: QualitativeText
    evidence_keys: list[EvidenceKey] = Field(min_length=1, max_length=3)


class OfficerNarrativeDraft(BaseModel):
    """Structured model output containing qualitative language only."""

    headline: QualitativeText
    summary: QualitativeText
    findings: list[OfficerFindingDraft] = Field(min_length=1, max_length=4)
    limitations: list[QualitativeText] = Field(min_length=1, max_length=3)


class OfficerEvidence(BaseModel):
    key: EvidenceKey
    label: str
    value: str
    source_type: Literal[
        "observed_historical_statistic",
        "model_assumption",
        "hypothetical_scenario_result",
    ]


class OfficerFinding(BaseModel):
    title: str
    explanation: str
    evidence: list[OfficerEvidence]


class RiskOfficerResponse(BaseModel):
    intent: OfficerIntent
    headline: str
    summary: str
    findings: list[OfficerFinding]
    limitations: list[str]
    parsed_scenario: ParsedRiskIntent | None
    stress_test: StressTestResponse | None
    narrative_source: Literal["openai_structured_output", "deterministic_rule_engine"]
    model: str
    numerical_policy: str = (
        "All displayed numerical values come from deterministic Python results or "
        "explicit user-supplied scenario inputs; the narrative layer never calculates "
        "financial metrics."
    )
    disclaimer: str = (
        "Risk explanations and hypothetical stress results are educational analytics, "
        "not predictions or personalized financial advice."
    )
