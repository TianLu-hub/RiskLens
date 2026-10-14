"""Chronological out-of-sample backtest endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.data.market_data import (
    InsufficientHistoryError,
    InvalidTickerError,
    MarketDataProvider,
    MarketDataUnavailableError,
    get_market_data_provider,
)
from app.models.backtest import BacktestRequest, BacktestResponse
from app.optimization.backtest import backtest_portfolio
from app.optimization.optimizer import OptimizationUnavailableError

router = APIRouter(tags=["backtest"])


@router.post("/portfolio/backtest", response_model=BacktestResponse)
def backtest(
    payload: BacktestRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> BacktestResponse:
    """Return a walk-forward comparison; never mutate the user's portfolio."""

    try:
        return backtest_portfolio(payload, provider)
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
            detail={
                "code": "INSUFFICIENT_HISTORY",
                "message": str(exc),
            },
        ) from exc
    except MarketDataUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MARKET_DATA_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
    except OptimizationUnavailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OPTIMIZATION_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
