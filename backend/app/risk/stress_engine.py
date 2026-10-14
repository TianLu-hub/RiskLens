"""Deterministic linear stress engine for Phase 2 hypothetical scenarios."""

from __future__ import annotations

from collections import defaultdict

from app.models.stress import (
    AssetStressContribution,
    FactorStressContribution,
    StressAssumption,
    StressScenarioInputs,
    StressTestRequest,
    StressTestResponse,
)

BOND_DURATION_MAP: dict[str, float] = {
    "TLT": 16.0,
    "IEF": 7.5,
    "SHY": 1.8,
    "BND": 6.5,
    "AGG": 6.0,
}

TECH_TICKERS: set[str] = {
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "GOOG",
    "META",
    "AMD",
    "AVGO",
    "AMZN",
}

ETF_TECH_EXPOSURE: dict[str, float] = {
    "SPY": 0.30,
    "QQQ": 0.55,
}

FACTOR_LABELS: dict[str, str] = {
    "broad_market": "Broad market shock",
    "technology": "Technology shock",
    "interest_rates": "Interest-rate duration shock",
    "ticker_specific": "Ticker-specific override",
    "shock_cap_adjustment": "Return floor / cap adjustment",
}


def run_stress_test(request: StressTestRequest) -> StressTestResponse:
    """Apply structured shocks and return a fully reconciled P&L decomposition.

    Broad-market, technology, and duration effects are additive. An explicit
    ticker shock is interpreted as the total stressed return for that ticker,
    overriding aggregate factor effects for that asset. This prevents a request
    such as "NVDA -30%, market -10%" from silently turning into NVDA -40%.
    """

    assumptions = _base_assumptions(request)
    assumption_ids = {assumption.id for assumption in assumptions}
    factor_totals: defaultdict[str, float] = defaultdict(float)
    asset_results: list[AssetStressContribution] = []

    for position in request.positions:
        ticker = position.ticker
        factor_shocks: dict[str, float] = {}

        if request.market_shock is not None:
            market_exposure = 0.0 if ticker in BOND_DURATION_MAP else 1.0
            factor_shocks["broad_market"] = request.market_shock * market_exposure

        if request.tech_shock is not None:
            tech_exposure = _tech_exposure(ticker)
            if tech_exposure:
                factor_shocks["technology"] = request.tech_shock * tech_exposure
                assumption_id = f"tech_exposure_{ticker}"
                if assumption_id not in assumption_ids:
                    assumptions.append(
                        StressAssumption(
                            id=assumption_id,
                            label=f"{ticker} technology exposure assumption",
                            value=f"{tech_exposure:.0%}",
                            source_type="fallback_modeling_assumption",
                            description=(
                                "Static fallback exposure used only for this hypothetical "
                                "technology-sector shock; it is not live holdings data."
                            ),
                        )
                    )
                    assumption_ids.add(assumption_id)

        if request.rates_shock_bps is not None and ticker in BOND_DURATION_MAP:
            duration = BOND_DURATION_MAP[ticker]
            yield_change = request.rates_shock_bps / 10_000.0
            factor_shocks["interest_rates"] = -duration * yield_change
            assumption_id = f"duration_{ticker}"
            if assumption_id not in assumption_ids:
                assumptions.append(
                    StressAssumption(
                        id=assumption_id,
                        label=f"{ticker} duration assumption",
                        value=f"{duration:.1f} years",
                        source_type="fallback_modeling_assumption",
                        description=(
                            "Static effective-duration fallback used in ΔP/P ≈ -DΔy; "
                            "it is not a real-time duration measurement."
                        ),
                    )
                )
                assumption_ids.add(assumption_id)

        aggregate_shock = sum(factor_shocks.values())
        if ticker in request.ticker_shocks:
            explicit_total = request.ticker_shocks[ticker]
            factor_shocks["ticker_specific"] = explicit_total - aggregate_shock
            aggregate_shock = explicit_total

        bounded_shock = min(max(aggregate_shock, -1.0), 1.0)
        if bounded_shock != aggregate_shock:
            factor_shocks["shock_cap_adjustment"] = bounded_shock - aggregate_shock
            aggregate_shock = bounded_shock

        portfolio_contribution = position.weight * aggregate_shock
        position_value_before = (
            request.portfolio_value * position.weight
            if request.portfolio_value is not None
            else None
        )
        position_pnl = (
            position_value_before * aggregate_shock
            if position_value_before is not None
            else None
        )
        position_value_after = (
            position_value_before + position_pnl
            if position_value_before is not None and position_pnl is not None
            else None
        )

        for factor, shock in factor_shocks.items():
            factor_totals[factor] += position.weight * shock

        asset_results.append(
            AssetStressContribution(
                ticker=ticker,
                weight=position.weight,
                estimated_asset_return=aggregate_shock,
                portfolio_contribution=portfolio_contribution,
                estimated_dollar_pnl=position_pnl,
                position_value_before=position_value_before,
                position_value_after=position_value_after,
                factor_shocks=factor_shocks,
            )
        )

    portfolio_return = sum(item.portfolio_contribution for item in asset_results)
    dollar_pnl = (
        request.portfolio_value * portfolio_return
        if request.portfolio_value is not None
        else None
    )
    portfolio_after = (
        request.portfolio_value + dollar_pnl
        if request.portfolio_value is not None and dollar_pnl is not None
        else None
    )

    factor_results = [
        FactorStressContribution(
            factor=factor,
            label=FACTOR_LABELS[factor],
            portfolio_contribution=contribution,
            estimated_dollar_pnl=(
                request.portfolio_value * contribution
                if request.portfolio_value is not None
                else None
            ),
        )
        for factor, contribution in factor_totals.items()
        if abs(contribution) > 1e-15
    ]

    return StressTestResponse(
        scenario_name=request.scenario_name,
        scenario_inputs=StressScenarioInputs(
            market_shock=request.market_shock,
            tech_shock=request.tech_shock,
            rates_shock_bps=request.rates_shock_bps,
            ticker_shocks=request.ticker_shocks,
        ),
        estimated_portfolio_return=portfolio_return,
        estimated_dollar_pnl=dollar_pnl,
        portfolio_value_before=request.portfolio_value,
        portfolio_value_after=portfolio_after,
        asset_contributions=asset_results,
        factor_contributions=factor_results,
        assumptions=assumptions,
        disclaimer=(
            "Simplified hypothetical stress scenario. Results are deterministic "
            "linear estimates based on user inputs and disclosed fallback assumptions; "
            "they are not predictions or personalized financial advice."
        ),
    )


def _tech_exposure(ticker: str) -> float:
    if ticker in TECH_TICKERS:
        return 1.0
    return ETF_TECH_EXPOSURE.get(ticker, 0.0)


def _base_assumptions(request: StressTestRequest) -> list[StressAssumption]:
    assumptions = [
        StressAssumption(
            id="hypothetical_classification",
            label="Scenario classification",
            value="Hypothetical",
            source_type="model_methodology",
            description=(
                "This scenario is not a forecast and does not reproduce a historical event."
            ),
        ),
        StressAssumption(
            id="linear_additive_model",
            label="Shock aggregation method",
            value="Linear and additive",
            source_type="model_methodology",
            description=(
                "Broad-market, technology, and duration effects are added without "
                "second-order, liquidity, volatility, or correlation feedback."
            ),
        ),
        StressAssumption(
            id="ticker_override",
            label="Ticker-specific shock treatment",
            value="Overrides total asset shock",
            source_type="model_methodology",
            description=(
                "An explicit ticker shock is treated as that asset's total stressed return, "
                "not as an additional shock on top of market and sector inputs."
            ),
        ),
    ]

    if request.market_shock is not None:
        assumptions.append(
            StressAssumption(
                id="broad_market_exposure",
                label="Broad-market exposure assumption",
                value="100% non-bond / 0% mapped bond ETFs",
                source_type="fallback_modeling_assumption",
                description=(
                    "The broad-market shock is applied fully to non-bond positions and "
                    "not applied to ETFs listed in the static duration map."
                ),
            )
        )
    if request.rates_shock_bps is not None:
        assumptions.append(
            StressAssumption(
                id="duration_method",
                label="Interest-rate method",
                value="ΔP/P ≈ -DΔy",
                source_type="model_methodology",
                description=(
                    "First-order duration approximation only; convexity and spread changes "
                    "are excluded."
                ),
            )
        )
    return assumptions
