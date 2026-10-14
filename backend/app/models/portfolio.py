"""Portfolio request models and input invariants."""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
WEIGHT_TOLERANCE = 1e-4


class Position(BaseModel):
    """One long-only portfolio position."""

    ticker: str = Field(min_length=1, max_length=15)
    weight: float = Field(ge=0.0, le=1.0)
    initial_value: float | None = Field(default=None, gt=0.0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not TICKER_PATTERN.fullmatch(ticker):
            raise ValueError(
                "Ticker must contain only letters, numbers, dots, or hyphens"
            )
        return ticker


class AnalyzeRequest(BaseModel):
    """Input contract for a historical portfolio analysis."""

    positions: list[Position] = Field(min_length=1, max_length=50)
    lookback_years: int = Field(default=3, ge=1, le=10)
    risk_free_rate: float = Field(default=0.04, ge=-0.10, le=0.50)
    confidence_level: float = Field(default=0.95, ge=0.90, le=0.999)

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
