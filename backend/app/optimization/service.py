"""Market-data orchestration and comparable historical portfolio profiles."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from app.data.market_data import MarketDataProvider
from app.models.optimization import (
    AllocationComparison,
    OptimizationMetrics,
    OptimizationResponse,
    OptimizeRequest,
)
from app.models.responses import DataQuality
from app.optimization.optimizer import optimize_weights
from app.risk.concentration import (
    effective_number_of_positions,
    herfindahl_hirschman_index,
)
from app.risk.metrics import (
    annualized_covariance,
    annualized_geometric_return,
    daily_returns,
    portfolio_returns,
    portfolio_volatility,
    sharpe_ratio,
)


def optimize_portfolio(
    request: OptimizeRequest, provider: MarketDataProvider
) -> OptimizationResponse:
    """Fit constrained weights and compare them on the same aligned sample."""

    tickers = [position.ticker for position in request.positions]
    current = np.asarray([position.weight for position in request.positions])
    end = datetime.now(UTC)
    start = end - timedelta(days=int(request.lookback_years * 365.25) + 10)
    history = provider.get_adjusted_prices(tickers, start, end)
    returns = daily_returns(history.prices[tickers])
    solution = optimize_weights(
        returns,
        current,
        request.objective,
        request.risk_free_rate,
        request.max_position_weight,
    )
    optimized = solution.weights
    warnings = list(history.warnings)
    if solution.covariance_regularized:
        warnings.append(
            "Sample covariance was singular or nearly singular; a small ridge "
            "was added for optimization only. Displayed risk uses sample covariance."
        )

    return OptimizationResponse(
        objective=request.objective,
        max_position_weight=request.max_position_weight,
        current=_profile(returns, current, request.risk_free_rate),
        optimized=_profile(returns, optimized, request.risk_free_rate),
        allocations=[
            AllocationComparison(
                ticker=ticker,
                current_weight=float(current[index]),
                optimized_weight=float(optimized[index]),
                weight_change=float(optimized[index] - current[index]),
            )
            for index, ticker in enumerate(tickers)
        ],
        one_way_turnover=float(np.abs(optimized - current).sum() / 2),
        data_quality=DataQuality(
            source=history.source,
            observations=len(returns),
            start_date=returns.index[0].date().isoformat(),
            end_date=returns.index[-1].date().isoformat(),
            requested_lookback_years=request.lookback_years,
            warnings=warnings,
        ),
        methodology=(
            "Long-only SLSQP optimization on aligned historical daily returns. "
            "Maximum Sharpe uses the same geometric annualization and sample "
            "covariance as displayed comparisons. Risk parity equalizes "
            "percentage volatility contributions."
        ),
        limitations=[
            "In-sample historical comparison, not an out-of-sample forecast.",
            "No transaction costs, taxes, slippage, or market-impact estimates.",
            "No short positions; optional cap applies to optimized weights only.",
        ],
    )


def _profile(
    asset_returns: pd.DataFrame, weights: np.ndarray, risk_free_rate: float
) -> OptimizationMetrics:
    series = portfolio_returns(asset_returns, weights)
    annual_return = annualized_geometric_return(series)
    volatility = portfolio_volatility(annualized_covariance(asset_returns), weights)
    return OptimizationMetrics(
        annualized_return=annual_return,
        annualized_volatility=volatility,
        sharpe_ratio=sharpe_ratio(annual_return, volatility, risk_free_rate),
        hhi=herfindahl_hirschman_index(weights),
        effective_positions=effective_number_of_positions(weights),
    )
