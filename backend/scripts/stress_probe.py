"""Independent acceptance checks for the deployment probe's fixed TLT case."""

import math

from app.models.stress import StressTestResponse

SCENARIO_NAME = "Deployment check (hypothetical)"


def validate_stress_response(result: StressTestResponse) -> None:
    """Check a disclosed 16-year fallback, +100 bps, $100,000 TLT scenario.

    These are fixed acceptance values, not a second risk engine. If the
    published fallback assumption changes intentionally, update this fixture.
    """

    def require(condition: bool) -> None:
        if not condition:
            raise ValueError("Stress deployment fixture does not match")

    def number(actual: float | None, expected: float) -> None:
        require(
            actual is not None
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
        )

    require(result.scenario_name == SCENARIO_NAME)
    require(result.scenario_classification == "hypothetical")
    require(result.historical_data_used is False)
    inputs = result.scenario_inputs
    require(inputs.market_shock is None and inputs.tech_shock is None)
    require(inputs.ticker_shocks == {})
    number(inputs.rates_shock_bps, 100)
    number(result.estimated_portfolio_return, -0.16)
    number(result.estimated_dollar_pnl, -16_000)
    number(result.portfolio_value_before, 100_000)
    number(result.portfolio_value_after, 84_000)

    require(len(result.asset_contributions) == 1)
    asset = result.asset_contributions[0]
    require(asset.ticker == "TLT")
    number(asset.weight, 1)
    number(asset.estimated_asset_return, -0.16)
    number(asset.portfolio_contribution, -0.16)
    number(asset.estimated_dollar_pnl, -16_000)
    number(asset.position_value_before, 100_000)
    number(asset.position_value_after, 84_000)
    require(set(asset.factor_shocks) == {"interest_rates"})
    number(asset.factor_shocks["interest_rates"], -0.16)

    require(len(result.factor_contributions) == 1)
    factor = result.factor_contributions[0]
    require(factor.factor == "interest_rates")
    number(factor.portfolio_contribution, -0.16)
    number(factor.estimated_dollar_pnl, -16_000)
    durations = [item for item in result.assumptions if item.id == "duration_TLT"]
    require(len(durations) == 1)
    require(durations[0].source_type == "fallback_modeling_assumption")
    require(durations[0].value == "16.0 years")
