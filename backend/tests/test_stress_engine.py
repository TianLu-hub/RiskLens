"""Phase 2 deterministic stress-engine tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.stress import StressTestRequest
from app.risk.stress_engine import run_stress_test


def test_positive_rate_shock_lowers_long_duration_bond_price() -> None:
    request = StressTestRequest(
        positions=[{"ticker": "TLT", "weight": 1.0}],
        portfolio_value=100_000,
        rates_shock_bps=100,
    )

    result = run_stress_test(request)

    assert result.asset_contributions[0].estimated_asset_return == pytest.approx(-0.16)
    assert result.estimated_portfolio_return == pytest.approx(-0.16)
    assert result.estimated_dollar_pnl == pytest.approx(-16_000)
    assert result.portfolio_value_after == pytest.approx(84_000)


def test_ticker_shock_applies_weighted_contribution_and_overrides_market() -> None:
    request = StressTestRequest(
        positions=[
            {"ticker": "NVDA", "weight": 0.30},
            {"ticker": "SPY", "weight": 0.70},
        ],
        market_shock=-0.10,
        ticker_shocks={"nvda": -0.30},
    )

    result = run_stress_test(request)
    nvda = next(item for item in result.asset_contributions if item.ticker == "NVDA")

    assert nvda.estimated_asset_return == pytest.approx(-0.30)
    assert nvda.portfolio_contribution == pytest.approx(0.30 * -0.30)
    assert result.estimated_portfolio_return == pytest.approx(-0.16)


@pytest.mark.parametrize(
    ("ticker", "inherited_return"), [("NVDA", -0.25), ("TLT", -0.16)]
)
def test_explicit_zero_cancels_factor_shocks_while_omitted_ticker_inherits(
    ticker: str,
    inherited_return: float,
) -> None:
    payload = {
        "positions": [
            {"ticker": ticker, "weight": 0.4},
            {"ticker": "SPY", "weight": 0.6},
        ],
        "portfolio_value": 100_000,
        "market_shock": -0.10,
        "tech_shock": -0.15,
        "rates_shock_bps": 100,
    }
    inherited = run_stress_test(StressTestRequest.model_validate(payload))
    overridden = run_stress_test(
        StressTestRequest.model_validate(payload | {"ticker_shocks": {ticker: 0.0}})
    )
    inherited_assets = {item.ticker: item for item in inherited.asset_contributions}
    overridden_assets = {item.ticker: item for item in overridden.asset_contributions}
    asset = overridden_assets[ticker]

    assert inherited.scenario_inputs.ticker_shocks == {}
    assert inherited_assets[ticker].estimated_asset_return == pytest.approx(
        inherited_return
    )
    assert overridden.scenario_inputs.ticker_shocks == {ticker: 0.0}
    assert asset.estimated_asset_return == 0.0
    assert asset.portfolio_contribution == 0.0
    assert asset.estimated_dollar_pnl == 0.0
    assert asset.position_value_after == asset.position_value_before
    assert asset.factor_shocks["ticker_specific"] == pytest.approx(-inherited_return)
    assert sum(asset.factor_shocks.values()) == pytest.approx(0.0)
    assert overridden_assets["SPY"] == inherited_assets["SPY"]
    assert overridden_assets["SPY"].estimated_asset_return == pytest.approx(-0.145)
    assert "ticker_specific" not in overridden_assets["SPY"].factor_shocks
    assert overridden.estimated_portfolio_return == pytest.approx(0.6 * -0.145)
    assert sum(
        item.portfolio_contribution for item in overridden.asset_contributions
    ) == pytest.approx(overridden.estimated_portfolio_return)
    assert sum(
        item.portfolio_contribution for item in overridden.factor_contributions
    ) == pytest.approx(overridden.estimated_portfolio_return)
    assert sum(
        item.estimated_dollar_pnl for item in overridden.factor_contributions
    ) == pytest.approx(overridden.estimated_dollar_pnl)


def test_total_asset_and_factor_contributions_reconcile() -> None:
    request = StressTestRequest(
        positions=[
            {"ticker": "AAPL", "weight": 0.25},
            {"ticker": "SPY", "weight": 0.35},
            {"ticker": "TLT", "weight": 0.40},
        ],
        portfolio_value=250_000,
        market_shock=-0.08,
        tech_shock=-0.15,
        rates_shock_bps=100,
        ticker_shocks={"AAPL": -0.20},
    )

    result = run_stress_test(request)
    asset_total = sum(
        item.portfolio_contribution for item in result.asset_contributions
    )
    factor_total = sum(
        item.portfolio_contribution for item in result.factor_contributions
    )

    assert asset_total == pytest.approx(result.estimated_portfolio_return)
    assert factor_total == pytest.approx(result.estimated_portfolio_return)
    assert result.estimated_dollar_pnl == pytest.approx(
        result.portfolio_value_before * result.estimated_portfolio_return
    )


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {"positions": [{"ticker": "SPY", "weight": 1.0}]},
            "At least one non-zero stress input",
        ),
        (
            {
                "positions": [{"ticker": "SPY", "weight": 1.0}],
                "market_shock": -1.2,
            },
            "greater than or equal to -1",
        ),
        (
            {
                "positions": [{"ticker": "SPY", "weight": 1.0}],
                "ticker_shocks": {"NVDA": -0.3},
            },
            "unknown: NVDA",
        ),
    ],
)
def test_invalid_scenario_inputs_are_rejected(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        StressTestRequest.model_validate(payload)


def test_fallback_assumptions_are_surfaced() -> None:
    request = StressTestRequest(
        positions=[
            {"ticker": "SPY", "weight": 0.6},
            {"ticker": "TLT", "weight": 0.4},
        ],
        tech_shock=-0.15,
        rates_shock_bps=100,
    )

    result = run_stress_test(request)
    assumptions = {item.id: item for item in result.assumptions}

    assert assumptions["tech_exposure_SPY"].value == "30%"
    assert assumptions["tech_exposure_SPY"].source_type == (
        "fallback_modeling_assumption"
    )
    assert assumptions["duration_TLT"].value == "16.0 years"
    assert assumptions["duration_TLT"].source_type == ("fallback_modeling_assumption")
    assert result.historical_data_used is False
    assert result.scenario_classification == "hypothetical"
