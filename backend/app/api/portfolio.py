"""Portfolio-analysis HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.data.market_data import (
    InsufficientHistoryError,
    InvalidTickerError,
    MarketDataProvider,
    MarketDataUnavailableError,
    get_market_data_provider,
)
from app.models.portfolio import AnalyzeRequest, normalize_ticker
from app.models.responses import (
    HistoryPoint,
    MarketHistoryResponse,
    PortfolioAnalysisResponse,
)
from app.services import analyze_portfolio

router = APIRouter(tags=["portfolio"])


@router.post("/portfolio/analyze", response_model=PortfolioAnalysisResponse)
def analyze(
    payload: AnalyzeRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> PortfolioAnalysisResponse:
    """Calculate Phase 1 analytics from aligned historical prices."""

    try:
        return analyze_portfolio(payload, provider)
    except InvalidTickerError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_TICKER",
                "message": str(exc),
                "tickers": exc.tickers,
            },
        ) from exc
    except InsufficientHistoryError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INSUFFICIENT_HISTORY", "message": str(exc)},
        ) from exc
    except MarketDataUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "MARKET_DATA_UNAVAILABLE", "message": str(exc)},
        ) from exc


@router.get("/market/history/{ticker}", response_model=MarketHistoryResponse)
def market_history(
    ticker: str = Path(min_length=1, max_length=15),
    lookback_years: int = Query(default=1, ge=1, le=10),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> MarketHistoryResponse:
    """Return normalized adjusted close history for a single ticker."""

    from datetime import UTC, datetime, timedelta

    try:
        normalized = normalize_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_TICKER", "message": str(exc)},
        ) from exc
    end = datetime.now(UTC)
    start = end - timedelta(days=int(lookback_years * 365.25) + 10)
    try:
        history = provider.get_adjusted_prices([normalized], start, end)
    except InvalidTickerError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "INVALID_TICKER",
                "message": str(exc),
                "tickers": exc.tickers,
            },
        ) from exc
    except InsufficientHistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    series = history.prices[normalized]
    return MarketHistoryResponse(
        ticker=normalized,
        source=history.source,
        history=[
            HistoryPoint(date=index.date().isoformat(), adjusted_close=float(value))
            for index, value in series.items()
        ],
    )
