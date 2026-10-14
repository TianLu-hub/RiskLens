"""Walk-forward portfolio evaluation without training/test overlap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from app.data.market_data import InsufficientHistoryError, MarketDataProvider
from app.models.backtest import (
    BacktestFold,
    BacktestMetrics,
    BacktestPoint,
    BacktestRequest,
    BacktestResponse,
)
from app.models.responses import DataQuality
from app.optimization.optimizer import optimize_weights
from app.risk.drawdown import maximum_drawdown
from app.risk.metrics import (
    TRADING_DAYS,
    annualized_geometric_return,
    daily_returns,
    sharpe_ratio,
)


@dataclass
class _Account:
    """Normalized wealth and live, drifted holdings weights."""

    wealth: float
    weights: np.ndarray
    turnover: float = 0.0
    costs: float = 0.0

    def rebalance(self, target: np.ndarray, cost_bps: float) -> float:
        one_way = float(np.abs(target - self.weights).sum() / 2)
        cost = self.wealth * (2 * one_way * cost_bps / 10_000)
        self.wealth -= cost
        self.costs += cost
        self.turnover += one_way
        self.weights = target.copy()
        return one_way

    def advance(self, returns: np.ndarray) -> None:
        gross = self.weights * (1 + returns)
        growth = float(gross.sum())
        self.wealth *= growth
        self.weights = gross / growth


def _metrics(
    wealth: list[float], risk_free_rate: float, turnover: float, costs: float
) -> BacktestMetrics:
    series = pd.Series(np.asarray(wealth[1:]) / np.asarray(wealth[:-1]) - 1)
    annual_return = annualized_geometric_return(series)
    volatility = (
        float(series.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(series) > 1 else 0.0
    )
    return BacktestMetrics(
        cumulative_return=wealth[-1] - 1,
        annualized_return=annual_return,
        annualized_volatility=volatility,
        sharpe_ratio=sharpe_ratio(annual_return, volatility, risk_free_rate),
        max_drawdown=maximum_drawdown(series),
        final_wealth=wealth[-1],
        total_one_way_turnover=turnover,
        total_cost_fraction_of_initial_capital=costs,
    )


def backtest_portfolio(
    request: BacktestRequest, provider: MarketDataProvider
) -> BacktestResponse:
    """Refit weights on trailing observations, then trade only on later dates."""

    tickers = [position.ticker for position in request.positions]
    initial = np.asarray(
        [position.weight for position in request.positions], dtype=float
    )
    initial /= initial.sum()
    end = datetime.now(UTC)
    start = end - timedelta(days=int(request.lookback_years * 365.25) + 10)
    history = provider.get_adjusted_prices(tickers, start, end)
    returns = daily_returns(history.prices[tickers])
    if len(returns) < request.training_days + request.rebalance_days:
        raise InsufficientHistoryError(
            f"Need at least {request.training_days + request.rebalance_days} aligned daily returns "
            "for one full out-of-sample window. Select a longer lookback or shorter training window."
        )

    current = _Account(wealth=1.0, weights=initial.copy())
    optimized = _Account(wealth=1.0, weights=initial.copy())
    current_wealth = [1.0]
    optimized_wealth = [1.0]
    spy_index = tickers.index("SPY") if "SPY" in tickers else None
    spy_wealth = [1.0] if spy_index is not None else None
    points: list[BacktestPoint] = []
    folds: list[BacktestFold] = []
    warnings = list(history.warnings)
    regularized = False

    for test_start in range(
        request.training_days, len(returns), request.rebalance_days
    ):
        test_end = min(test_start + request.rebalance_days, len(returns))
        train = returns.iloc[test_start - request.training_days : test_start]
        test = returns.iloc[test_start:test_end]
        solution = optimize_weights(
            train,
            initial,
            request.objective,
            request.risk_free_rate,
            request.max_position_weight,
        )
        regularized |= solution.covariance_regularized
        current_turnover = current.rebalance(initial, request.cost_bps)
        optimized_turnover = optimized.rebalance(solution.weights, request.cost_bps)
        folds.append(
            BacktestFold(
                train_start=train.index[0].date().isoformat(),
                train_end=train.index[-1].date().isoformat(),
                test_start=test.index[0].date().isoformat(),
                test_end=test.index[-1].date().isoformat(),
                optimized_weights=dict(
                    zip(tickers, map(float, solution.weights), strict=True)
                ),
                optimized_one_way_turnover=optimized_turnover,
                current_one_way_turnover=current_turnover,
            )
        )
        for date, row in test.iterrows():
            asset_return = row.to_numpy(dtype=float)
            current.advance(asset_return)
            optimized.advance(asset_return)
            current_wealth.append(current.wealth)
            optimized_wealth.append(optimized.wealth)
            if spy_wealth is not None and spy_index is not None:
                spy_wealth.append(spy_wealth[-1] * (1 + asset_return[spy_index]))
            points.append(
                BacktestPoint(
                    date=date.date().isoformat(),
                    current_wealth=current.wealth,
                    optimized_wealth=optimized.wealth,
                    spy_wealth=spy_wealth[-1] if spy_wealth is not None else None,
                )
            )

    if regularized:
        warnings.append(
            "At least one training covariance matrix was regularized for optimization."
        )
    if len(returns) - request.training_days < request.rebalance_days * 2:
        warnings.append(
            "Fewer than two full forward windows were available; comparisons are unstable."
        )
    benchmark = (
        _metrics(spy_wealth, request.risk_free_rate, 0.0, 0.0) if spy_wealth else None
    )
    return BacktestResponse(
        objective=request.objective,
        current=_metrics(
            current_wealth, request.risk_free_rate, current.turnover, current.costs
        ),
        optimized=_metrics(
            optimized_wealth,
            request.risk_free_rate,
            optimized.turnover,
            optimized.costs,
        ),
        spy_buy_and_hold=benchmark,
        series=points,
        folds=folds,
        data_quality=DataQuality(
            source=history.source,
            observations=len(returns),
            start_date=returns.index[0].date().isoformat(),
            end_date=returns.index[-1].date().isoformat(),
            requested_lookback_years=request.lookback_years,
            warnings=warnings,
        ),
        training_days=request.training_days,
        rebalance_days=request.rebalance_days,
        cost_bps=request.cost_bps,
        methodology=(
            "At each rebalance, fit on the prior trailing daily returns ending before the first "
            "test day. Hold drifted weights through the forward window. Rebalance both optimized "
            "and fixed-current portfolios at window boundaries. Charge costs on total traded "
            "notional (twice one-way turnover). SPY, when present, is buy-and-hold with no costs."
        ),
        limitations=[
            "Historical hypothetical simulation, not actual trading or a future forecast.",
            "Rebalancing before the next observed daily return at a modeled close and flat "
            "basis-point costs are simplifying assumptions.",
            "No taxes, spreads, slippage, market impact, or survivorship-bias correction.",
            "Current holdings and tickers were chosen today; that selection can embed hindsight.",
        ],
    )
