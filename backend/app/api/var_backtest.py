"""One-day historical VaR validation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.data.market_data import (
    InsufficientHistoryError,
    InvalidTickerError,
    MarketDataProvider,
    MarketDataUnavailableError,
    get_market_data_provider,
)
from app.models.var_backtest import VarBacktestRequest, VarBacktestResponse
from app.risk.var_backtest import backtest_var_portfolio

router = APIRouter(tags=["var-backtest"])


@router.post("/portfolio/var-backtest", response_model=VarBacktestResponse)
def var_backtest(
    payload: VarBacktestRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> VarBacktestResponse:
    """Evaluate rolling historical VaR on subsequent daily portfolio returns."""

    try:
        return backtest_var_portfolio(payload, provider)
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
