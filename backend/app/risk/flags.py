"""Transparent, rule-based risk flags independent of any language model."""

from __future__ import annotations

from app.models.responses import RiskFlag


def build_risk_flags(
    *,
    effective_positions: float,
    max_pairwise_correlation: float | None,
    max_risk_contribution: float,
    var_value: float,
    cvar_value: float,
) -> list[RiskFlag]:
    """Evaluate deterministic Phase 1 risk thresholds."""

    flags: list[RiskFlag] = []
    if effective_positions < 3.0:
        flags.append(
            RiskFlag(
                code="HIGH_CONCENTRATION",
                severity="high",
                title="High concentration",
                detail=f"Effective position count is {effective_positions:.2f}, below 3.0.",
            )
        )
    if max_pairwise_correlation is not None and max_pairwise_correlation > 0.75:
        flags.append(
            RiskFlag(
                code="HIGH_CORRELATION",
                severity="medium",
                title="High correlation",
                detail=f"Maximum pairwise correlation is {max_pairwise_correlation:.2f}.",
            )
        )
    if max_risk_contribution > 0.35:
        flags.append(
            RiskFlag(
                code="RISK_DOMINATED",
                severity="high",
                title="Risk dominated by one asset",
                detail=f"The largest volatility contribution is {max_risk_contribution:.1%}.",
            )
        )
    if var_value > 0 and cvar_value > 1.5 * var_value:
        flags.append(
            RiskFlag(
                code="ELEVATED_TAIL_RISK",
                severity="medium",
                title="Elevated tail risk",
                detail="Expected shortfall exceeds 1.5 times historical VaR.",
            )
        )
    return flags
