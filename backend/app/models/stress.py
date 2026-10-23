"""Typed contracts for deterministic hypothetical stress tests."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.portfolio import Position, TICKER_PATTERN, WEIGHT_TOLERANCE


class StressTestRequest(BaseModel):
    """Portfolio holdings plus a structured hypothetical scenario."""

    positions: list[Position] = Field(min_length=1, max_length=50)
    portfolio_value: float | None = Field(default=None, gt=0.0, le=1_000_000_000_000)
    scenario_name: str = Field(default="Custom Scenario", min_length=1, max_length=100)
    market_shock: float | None = Field(default=None, ge=-1.0, le=1.0)
    tech_shock: float | None = Field(default=None, ge=-1.0, le=1.0)
    rates_shock_bps: float | None = Field(default=None, ge=-1_000.0, le=1_000.0)
    ticker_shocks: dict[str, float] = Field(default_factory=dict)

    @field_validator("scenario_name")
    @classmethod
    def clean_scenario_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("ticker_shocks", mode="before")
    @classmethod
    def normalize_ticker_shocks(cls, value: object) -> object:
        if value is None:
            return {}
        if not isinstance(value, dict):
            return value

        normalized: dict[str, float] = {}
        for raw_ticker, raw_shock in value.items():
            ticker = str(raw_ticker).strip().upper()
            if not TICKER_PATTERN.fullmatch(ticker):
                raise ValueError(
                    "Ticker shock keys must contain only letters, numbers, dots, or hyphens"
                )
            if ticker in normalized:
                raise ValueError("Each ticker shock may appear only once")
            # bool is a numeric subtype in Python, but not a financial shock.
            if isinstance(raw_shock, bool):
                raise ValueError("Ticker shocks must be numeric, not boolean")
            try:
                shock = float(raw_shock)
            except (TypeError, ValueError, OverflowError) as exc:
                # Pydantic does not turn TypeError into a validation response.
                raise ValueError("Ticker shocks must be numeric") from exc
            if not -1.0 <= shock <= 1.0:
                raise ValueError("Ticker shocks must be between -1.0 and 1.0")
            normalized[ticker] = shock
        return normalized

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        tickers = [position.ticker for position in self.positions]
        if len(tickers) != len(set(tickers)):
            raise ValueError("Each ticker may appear only once")

        total_weight = sum(position.weight for position in self.positions)
        if abs(total_weight - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(
                f"Portfolio weights must sum to 1.0; received {total_weight:.6f}"
            )

        unknown_tickers = sorted(set(self.ticker_shocks) - set(tickers))
        if unknown_tickers:
            raise ValueError(
                "Ticker shocks must reference portfolio positions; unknown: "
                + ", ".join(unknown_tickers)
            )

        shocks = [self.market_shock, self.tech_shock]
        has_percentage_shock = any(
            value is not None and abs(value) > 1e-12 for value in shocks
        )
        has_rate_shock = (
            self.rates_shock_bps is not None and abs(self.rates_shock_bps) > 1e-12
        )
        has_ticker_shock = any(
            abs(value) > 1e-12 for value in self.ticker_shocks.values()
        )
        if not (has_percentage_shock or has_rate_shock or has_ticker_shock):
            raise ValueError("At least one non-zero stress input is required")
        return self


class StressScenarioInputs(BaseModel):
    market_shock: float | None
    tech_shock: float | None
    rates_shock_bps: float | None
    ticker_shocks: dict[str, float]


class StressAssumption(BaseModel):
    id: str
    label: str
    value: str
    source_type: Literal[
        "user_input", "fallback_modeling_assumption", "model_methodology"
    ]
    description: str


class AssetStressContribution(BaseModel):
    ticker: str
    weight: float
    estimated_asset_return: float
    portfolio_contribution: float
    estimated_dollar_pnl: float | None
    position_value_before: float | None
    position_value_after: float | None
    factor_shocks: dict[str, float]


class FactorStressContribution(BaseModel):
    factor: str
    label: str
    portfolio_contribution: float
    estimated_dollar_pnl: float | None


class StressTestResponse(BaseModel):
    scenario_name: str
    scenario_classification: Literal["hypothetical"] = "hypothetical"
    historical_data_used: bool = False
    scenario_inputs: StressScenarioInputs
    estimated_portfolio_return: float
    estimated_dollar_pnl: float | None
    portfolio_value_before: float | None
    portfolio_value_after: float | None
    asset_contributions: list[AssetStressContribution]
    factor_contributions: list[FactorStressContribution]
    assumptions: list[StressAssumption]
    disclaimer: str
