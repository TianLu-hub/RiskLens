"""Convert a structured LLM intent into validated deterministic stress inputs."""

from __future__ import annotations

from pydantic import ValidationError

from app.models.ai import OfficerIntent, ParsedRiskIntent, RiskOfficerRequest
from app.models.stress import StressTestRequest


class ScenarioInterpretationError(ValueError):
    """Raised when interpreted scenario fields cannot be safely executed."""


def build_stress_request(
    intent: ParsedRiskIntent, request: RiskOfficerRequest
) -> StressTestRequest | None:
    """Validate translated inputs before they reach the deterministic risk engine."""

    if intent.intent is not OfficerIntent.STRESS_SCENARIO:
        return None

    ticker_shocks: dict[str, float] = {}
    for item in intent.ticker_shocks:
        ticker = item.ticker.strip().upper()
        if ticker in ticker_shocks:
            raise ScenarioInterpretationError(
                f"The scenario contains more than one shock for {ticker}."
            )
        ticker_shocks[ticker] = item.shock

    try:
        return StressTestRequest(
            positions=request.positions,
            portfolio_value=request.portfolio_value,
            scenario_name=intent.scenario_name or "AI-interpreted custom scenario",
            market_shock=intent.market_shock,
            tech_shock=intent.tech_shock,
            rates_shock_bps=intent.rates_shock_bps,
            ticker_shocks=ticker_shocks,
        )
    except ValidationError as error:
        messages = "; ".join(
            str(item.get("msg", "Invalid scenario input")) for item in error.errors()
        )
        raise ScenarioInterpretationError(messages) from error
