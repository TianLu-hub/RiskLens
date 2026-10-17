"""Application services that compose deterministic risk calculations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from app.data.market_data import MarketDataProvider
from app.models.portfolio import AnalyzeRequest
from app.models.responses import (
    ConcentrationResult,
    CorrelationPair,
    CorrelationResult,
    DataQuality,
    DrawdownResult,
    FactorExposureResult,
    PortfolioAnalysisResponse,
    RiskContributionItem,
    RiskMetrics,
    TimeSeriesPoint,
)
from app.risk.concentration import (
    effective_number_of_positions,
    herfindahl_hirschman_index,
    top_n_concentration,
)
from app.risk.contribution import volatility_risk_contributions
from app.risk.correlation import correlation_matrix, strongest_pairs
from app.risk.drawdown import drawdown_series, wealth_index
from app.risk.factors import (
    DEFAULT_ROLLING_WINDOW,
    MARKET_BENCHMARK,
    MarketFactorEstimate,
    market_factor_regression,
)
from app.risk.flags import build_risk_flags
from app.risk.metrics import (
    annualized_covariance,
    annualized_geometric_return,
    daily_returns,
    portfolio_returns,
    portfolio_volatility,
    sharpe_ratio,
)
from app.risk.var import historical_cvar, historical_var


def analyze_portfolio(
    request: AnalyzeRequest, provider: MarketDataProvider
) -> PortfolioAnalysisResponse:
    """Fetch prices once and calculate the complete Phase 1 response."""

    tickers = [position.ticker for position in request.positions]
    weights = np.asarray(
        [position.weight for position in request.positions], dtype=float
    )
    end = datetime.now(UTC)
    # Calendar-day buffer captures the requested number of trading years.
    start = end - timedelta(days=int(request.lookback_years * 365.25) + 10)
    history = provider.get_adjusted_prices(tickers, start, end)
    prices = history.prices[tickers]
    asset_returns = daily_returns(prices)
    portfolio_return_series = portfolio_returns(asset_returns, weights)

    annual_return = annualized_geometric_return(portfolio_return_series)
    covariance = annualized_covariance(asset_returns)
    volatility = portfolio_volatility(covariance, weights)
    sharpe = sharpe_ratio(annual_return, volatility, request.risk_free_rate)
    var_value = historical_var(portfolio_return_series, request.confidence_level)
    cvar_value = historical_cvar(portfolio_return_series, request.confidence_level)

    wealth = wealth_index(portfolio_return_series)
    drawdowns = drawdown_series(portfolio_return_series)
    correlations = correlation_matrix(asset_returns)
    pairs = strongest_pairs(correlations)
    contributions = volatility_risk_contributions(covariance, weights)
    factor_estimate, benchmark_source = _market_factor_exposure(
        provider=provider,
        tickers=tickers,
        asset_returns=asset_returns,
        portfolio_return_series=portfolio_return_series,
        annual_risk_free_rate=request.risk_free_rate,
        start=start,
        end=end,
        portfolio_source=history.source,
    )

    hhi = herfindahl_hirschman_index(weights)
    effective_positions = effective_number_of_positions(weights)
    largest_index = int(np.argmax(weights))
    max_correlation = float(pairs[0]["correlation"]) if pairs else None
    max_contribution = float(contributions["risk_contribution"].max())

    warnings = list(history.warnings)
    if sharpe is None:
        warnings.append(
            "Portfolio volatility is zero; the Sharpe ratio is unavailable."
        )
    if correlations.isna().any().any():
        warnings.append(
            "At least one asset has zero return variance; some correlations are unavailable."
        )

    return PortfolioAnalysisResponse(
        metrics=RiskMetrics(
            annualized_return=annual_return,
            annualized_volatility=volatility,
            sharpe_ratio=sharpe,
            var=var_value,
            cvar=cvar_value,
            confidence_level=request.confidence_level,
            risk_free_rate=request.risk_free_rate,
        ),
        performance=_series_points(wealth - 1.0),
        drawdown=DrawdownResult(
            current_drawdown=float(drawdowns.iloc[-1]),
            max_drawdown=float(drawdowns.min()),
            series=_series_points(drawdowns),
        ),
        correlation=CorrelationResult(
            tickers=tickers,
            matrix=_finite_matrix(correlations.loc[tickers, tickers]),
            highest_correlations=[CorrelationPair(**pair) for pair in pairs],
        ),
        risk_contributions=[
            RiskContributionItem(
                ticker=ticker,
                weight=float(weights[index]),
                marginal_risk=float(contributions.loc[ticker, "marginal_risk"]),
                absolute_risk_contribution=float(
                    contributions.loc[ticker, "absolute_risk_contribution"]
                ),
                risk_contribution=float(contributions.loc[ticker, "risk_contribution"]),
            )
            for index, ticker in enumerate(tickers)
        ],
        concentration=ConcentrationResult(
            hhi=hhi,
            effective_positions=effective_positions,
            largest_position=float(weights[largest_index]),
            largest_position_ticker=tickers[largest_index],
            top_3_concentration=top_n_concentration(weights),
            position_count=len(weights),
        ),
        factor_exposure=FactorExposureResult(
            benchmark_source=benchmark_source,
            available=factor_estimate.available,
            alpha_annualized=factor_estimate.alpha_annualized,
            market_beta=factor_estimate.market_beta,
            r_squared=factor_estimate.r_squared,
            idiosyncratic_volatility=factor_estimate.idiosyncratic_volatility,
            observations=factor_estimate.observations,
            rolling_window_days=DEFAULT_ROLLING_WINDOW,
            rolling_beta=_series_points(factor_estimate.rolling_beta),
            unavailable_reason=factor_estimate.unavailable_reason,
        ),
        risk_flags=build_risk_flags(
            effective_positions=effective_positions,
            max_pairwise_correlation=max_correlation,
            max_risk_contribution=max_contribution,
            var_value=var_value,
            cvar_value=cvar_value,
        ),
        data_quality=DataQuality(
            provenance=history.provenance,
            source=history.source,
            observations=len(asset_returns),
            start_date=asset_returns.index[0].date().isoformat(),
            end_date=asset_returns.index[-1].date().isoformat(),
            requested_lookback_years=request.lookback_years,
            warnings=warnings,
        ),
    )


def _market_factor_exposure(
    *,
    provider: MarketDataProvider,
    tickers: list[str],
    asset_returns: pd.DataFrame,
    portfolio_return_series: pd.Series,
    annual_risk_free_rate: float,
    start: datetime,
    end: datetime,
    portfolio_source: str,
) -> tuple[MarketFactorEstimate, str | None]:
    """Calculate SPY exposure without allowing benchmark failure to break Phase 1."""

    if MARKET_BENCHMARK in tickers:
        benchmark_returns = asset_returns[MARKET_BENCHMARK]
        benchmark_source = portfolio_source
    else:
        try:
            benchmark_history = provider.get_adjusted_prices(
                [MARKET_BENCHMARK], start, end
            )
            benchmark_returns = daily_returns(
                benchmark_history.prices[[MARKET_BENCHMARK]]
            )[MARKET_BENCHMARK]
            benchmark_source = benchmark_history.source
        except Exception:
            unavailable = MarketFactorEstimate(
                available=False,
                alpha_annualized=None,
                market_beta=None,
                r_squared=None,
                idiosyncratic_volatility=None,
                observations=0,
                rolling_beta=pd.Series(dtype=float, name="rolling_beta"),
                unavailable_reason=(
                    "SPY benchmark history is unavailable; core portfolio analytics "
                    "remain valid."
                ),
            )
            return unavailable, None

    return (
        market_factor_regression(
            portfolio_return_series,
            benchmark_returns,
            annual_risk_free_rate,
        ),
        benchmark_source,
    )


def _series_points(series: pd.Series) -> list[TimeSeriesPoint]:
    return [
        TimeSeriesPoint(date=index.date().isoformat(), value=float(value))
        for index, value in series.items()
    ]


def _finite_matrix(matrix: pd.DataFrame) -> list[list[float]]:
    """Serialize NaN correlations as zero while preserving diagonal identity."""

    values = matrix.to_numpy(dtype=float)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(values, 1.0)
    return values.tolist()
