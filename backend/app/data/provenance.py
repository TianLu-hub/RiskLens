"""Provider-reported provenance; absent metadata must never imply fresh data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AssetCoverage(BaseModel):
    ticker: str
    observed_prices: int = Field(ge=0)
    missing_prices: int = Field(ge=0)
    filled_prices: int = Field(ge=0)
    first_observed_date: str
    last_observed_date: str


class MarketDataProvenance(BaseModel):
    """Counts refer to provider-returned rows, not an exchange calendar audit."""

    data_type: Literal["historical", "synthetic"]
    fetched_at: datetime
    cache_hit: bool
    cache_ttl_seconds: int = Field(ge=0)
    price_basis: Literal["adjusted_close", "unadjusted_close"]
    price_start_date: str
    price_end_date: str
    raw_price_rows: int = Field(ge=0)
    aligned_price_rows: int = Field(ge=0)
    dropped_price_rows: int = Field(ge=0)
    forward_fill_limit: int = Field(ge=0)
    assets: list[AssetCoverage]
