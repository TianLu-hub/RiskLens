"""Independent historical allocation-comparison endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.data.market_data import (
    InsufficientHistoryError,
    InvalidTickerError,
    MarketDataProvider,
    MarketDataUnavailableError,
    get_market_data_provider,
)
from app.models.optimization import OptimizationResponse, OptimizeRequest
from app.optimization.optimizer import OptimizationUnavailableError
from app.optimization.service import optimize_portfolio

router = APIRouter(tags=["optimization"])


@router.post("/portfolio/optimize", response_model=OptimizationResponse)
def optimize(
    payload: OptimizeRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> OptimizationResponse:
    """Compare, without applying, an optimized long-only allocation."""

    try:
        return optimize_portfolio(payload, provider)
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
    except OptimizationUnavailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "OPTIMIZATION_UNAVAILABLE", "message": str(exc)},
        ) from exc
