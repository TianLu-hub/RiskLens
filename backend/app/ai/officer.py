"""Orchestration and guardrails for the AI Portfolio Risk Officer."""

from __future__ import annotations

import json
import logging
import os
from typing import Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import ValidationError

from app.ai.scenario_parser import build_stress_request
from app.models.ai import (
    EvidenceKey,
    OfficerEvidence,
    OfficerFinding,
    OfficerIntent,
    OfficerNarrativeDraft,
    ParsedRiskIntent,
    RiskOfficerAnalysisContext,
    RiskOfficerRequest,
    RiskOfficerResponse,
)
from app.models.stress import StressTestResponse
from app.risk.stress_engine import run_stress_test

INTENT_SYSTEM_PROMPT = """You interpret requests for a portfolio risk application.
Return only the requested structured object. Classify the request as stress_scenario only
when the user supplies at least one explicit numerical shock. Otherwise use
portfolio_analysis. Translate user-supplied percentages to decimal returns and preserve
basis-point values. A drop, fall, decline, or selloff is negative; a rate rise is positive.
Do not infer missing magnitudes, calculate portfolio effects, or add securities. Only accept
ticker shocks for the supplied portfolio tickers. All unused fields must be null and
ticker_shocks must be an empty list. This is interpretation, not financial advice."""

OFFICER_SYSTEM_PROMPT = """You are an AI Portfolio Risk Officer.
Use only the supplied structured quantitative results. Never calculate or invent a number.
Your prose must contain no digits, percentages, currency amounts, or numeric metric values;
the application will attach deterministic evidence separately. Select evidence keys that
directly support each finding. Distinguish observed historical statistics, disclosed model
assumptions, and hypothetical scenario results. If factor exposure is absent, say it is
unavailable. Do not recommend buying or selling securities and do not give personalized
financial advice. Answer in the same language as the user's question. Use concise,
institutional language and identify the dominant risk rather than repeating every field."""

logger = logging.getLogger(__name__)


class AIConfigurationError(RuntimeError):
    """Raised when the OpenAI-backed feature has not been configured."""


class AIProviderError(RuntimeError):
    """Safe, user-facing classification of an OpenAI provider failure."""

    def __init__(self, code: str, public_message: str, *, stage: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.stage = stage


class RiskOfficerAI(Protocol):
    model: str
    narrative_source: str

    def parse_intent(self, question: str, tickers: list[str]) -> ParsedRiskIntent: ...

    def create_narrative(
        self,
        question: str,
        analysis: RiskOfficerAnalysisContext,
        stress_test: StressTestResponse | None,
    ) -> OfficerNarrativeDraft: ...


class OpenAIRiskOfficer:
    """OpenAI Responses API adapter with Pydantic structured outputs."""

    narrative_source = "openai_structured_output"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise AIConfigurationError(
                "The AI Risk Officer is not configured. Set OPENAI_API_KEY on the backend."
            )
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=key, timeout=30.0, max_retries=2)

    def parse_intent(self, question: str, tickers: list[str]) -> ParsedRiskIntent:
        payload = {
            "question": question,
            "portfolio_tickers": tickers,
        }
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload)},
                ],
                text_format=ParsedRiskIntent,
            )
        except Exception as error:  # SDK errors are normalized before crossing the API.
            raise _classify_provider_error(error, stage="intent_parsing") from error
        if response.output_parsed is None:
            raise AIProviderError(
                "AI_RESPONSE_INVALID",
                "OpenAI did not return a validated scenario interpretation. Retry the request.",
                stage="intent_parsing",
            )
        return response.output_parsed

    def create_narrative(
        self,
        question: str,
        analysis: RiskOfficerAnalysisContext,
        stress_test: StressTestResponse | None,
    ) -> OfficerNarrativeDraft:
        payload = {
            "question": question,
            "calculated_analysis": analysis.model_dump(mode="json"),
            "calculated_stress_test": (
                stress_test.model_dump(mode="json") if stress_test is not None else None
            ),
            "available_evidence_keys": [key.value for key in EvidenceKey],
        }
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": OFFICER_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload)},
                ],
                text_format=OfficerNarrativeDraft,
            )
        except Exception as error:  # Includes schema validation and provider failures.
            raise _classify_provider_error(
                error, stage="narrative_generation"
            ) from error
        if response.output_parsed is None:
            raise AIProviderError(
                "AI_RESPONSE_INVALID",
                "OpenAI did not return a validated risk explanation. Retry the request.",
                stage="narrative_generation",
            )
        return response.output_parsed


def _classify_provider_error(error: Exception, *, stage: str) -> AIProviderError:
    """Map provider failures to safe diagnostics without exposing secrets or prompts."""

    status = error.status_code if isinstance(error, APIStatusError) else None
    provider_code = error.code if isinstance(error, APIStatusError) else None
    request_id = error.request_id if isinstance(error, APIStatusError) else None
    logger.warning(
        "OpenAI Risk Officer failure: stage=%s type=%s status=%s code=%s request_id=%s",
        stage,
        type(error).__name__,
        status,
        provider_code,
        request_id,
    )

    if isinstance(error, AuthenticationError):
        return AIProviderError(
            "AI_AUTHENTICATION_FAILED",
            "OpenAI rejected the backend API key. Replace it with a valid project API key.",
            stage=stage,
        )
    if isinstance(error, PermissionDeniedError):
        return AIProviderError(
            "AI_PERMISSION_DENIED",
            "The OpenAI project does not permit this model or operation.",
            stage=stage,
        )
    if isinstance(error, RateLimitError):
        if provider_code in {"insufficient_quota", "credit_balance_exhausted"}:
            return AIProviderError(
                "AI_QUOTA_EXCEEDED",
                "OpenAI API quota is unavailable. Add API billing or credits and check the project usage limit.",
                stage=stage,
            )
        return AIProviderError(
            "AI_RATE_LIMITED",
            "OpenAI temporarily rate-limited the request. Wait briefly and try again.",
            stage=stage,
        )
    if isinstance(error, NotFoundError):
        return AIProviderError(
            "AI_MODEL_UNAVAILABLE",
            "The configured OpenAI model is unavailable to this API project.",
            stage=stage,
        )
    if isinstance(error, APITimeoutError):
        return AIProviderError(
            "AI_TIMEOUT",
            "OpenAI did not respond before the backend timeout. Retry the request.",
            stage=stage,
        )
    if isinstance(error, APIConnectionError):
        return AIProviderError(
            "AI_CONNECTION_FAILED",
            "The backend could not reach OpenAI. Retry after checking outbound connectivity.",
            stage=stage,
        )
    if isinstance(error, (BadRequestError, ValidationError)):
        return AIProviderError(
            "AI_RESPONSE_INVALID",
            "OpenAI could not satisfy the Risk Officer structured response contract.",
            stage=stage,
        )
    return AIProviderError(
        "AI_PROVIDER_ERROR",
        "The OpenAI service could not complete the Risk Officer request.",
        stage=stage,
    )


def get_risk_officer_ai() -> RiskOfficerAI:
    """FastAPI dependency factory kept separate for deterministic test doubles."""

    provider = os.getenv("AI_PROVIDER", "deterministic").strip().lower()
    if provider == "deterministic":
        from app.ai.deterministic_officer import DeterministicRiskOfficer

        return DeterministicRiskOfficer()
    if provider == "openai":
        return OpenAIRiskOfficer()
    raise AIConfigurationError(
        "AI_PROVIDER must be either 'deterministic' or 'openai'."
    )


def answer_risk_question(
    request: RiskOfficerRequest, provider: RiskOfficerAI
) -> RiskOfficerResponse:
    """Interpret intent, run Python stress math when needed, then explain results."""

    tickers = [position.ticker for position in request.positions]
    parsed_intent = provider.parse_intent(request.question, tickers)
    stress_request = build_stress_request(parsed_intent, request)
    stress_test = (
        run_stress_test(stress_request) if stress_request is not None else None
    )
    narrative = provider.create_narrative(
        request.question, request.analysis, stress_test
    )
    evidence = _build_evidence_catalog(request.analysis, stress_test)

    findings: list[OfficerFinding] = []
    for finding in narrative.findings:
        selected_evidence = [
            evidence[key] for key in finding.evidence_keys if key in evidence
        ]
        if not selected_evidence:
            selected_evidence = [evidence[EvidenceKey.ANNUALIZED_VOLATILITY]]
        findings.append(
            OfficerFinding(
                title=finding.title,
                explanation=finding.explanation,
                evidence=selected_evidence,
            )
        )

    return RiskOfficerResponse(
        intent=parsed_intent.intent,
        headline=narrative.headline,
        summary=narrative.summary,
        findings=findings,
        limitations=narrative.limitations,
        parsed_scenario=(
            parsed_intent
            if parsed_intent.intent is OfficerIntent.STRESS_SCENARIO
            else None
        ),
        stress_test=stress_test,
        narrative_source=provider.narrative_source,
        model=provider.model,
    )


def _build_evidence_catalog(
    analysis: RiskOfficerAnalysisContext,
    stress_test: StressTestResponse | None,
) -> dict[EvidenceKey, OfficerEvidence]:
    metrics = analysis.metrics
    concentration = analysis.concentration
    highest_correlation = (
        analysis.correlation.highest_correlations[0]
        if analysis.correlation.highest_correlations
        else None
    )
    largest_risk = max(
        analysis.risk_contributions,
        key=lambda item: item.risk_contribution,
    )
    historical = "observed_historical_statistic"
    catalog: dict[EvidenceKey, OfficerEvidence] = {
        EvidenceKey.ANNUALIZED_RETURN: OfficerEvidence(
            key=EvidenceKey.ANNUALIZED_RETURN,
            label="Annualized return",
            value=_percent(metrics.annualized_return),
            source_type=historical,
        ),
        EvidenceKey.ANNUALIZED_VOLATILITY: OfficerEvidence(
            key=EvidenceKey.ANNUALIZED_VOLATILITY,
            label="Annualized volatility",
            value=_percent(metrics.annualized_volatility),
            source_type=historical,
        ),
        EvidenceKey.SHARPE_RATIO: OfficerEvidence(
            key=EvidenceKey.SHARPE_RATIO,
            label="Annualized Sharpe estimate",
            value=(
                f"{metrics.sharpe_ratio:.2f}"
                if metrics.sharpe_ratio is not None
                else "Unavailable"
            ),
            source_type=historical,
        ),
        EvidenceKey.VAR: OfficerEvidence(
            key=EvidenceKey.VAR,
            label=f"{metrics.confidence_level:.0%} one-day historical VaR",
            value=_percent(metrics.var),
            source_type=historical,
        ),
        EvidenceKey.CVAR: OfficerEvidence(
            key=EvidenceKey.CVAR,
            label=f"{metrics.confidence_level:.0%} one-day expected shortfall",
            value=_percent(metrics.cvar),
            source_type=historical,
        ),
        EvidenceKey.MAX_DRAWDOWN: OfficerEvidence(
            key=EvidenceKey.MAX_DRAWDOWN,
            label="Maximum historical drawdown",
            value=_percent(analysis.drawdown.max_drawdown),
            source_type=historical,
        ),
        EvidenceKey.CURRENT_DRAWDOWN: OfficerEvidence(
            key=EvidenceKey.CURRENT_DRAWDOWN,
            label="Current drawdown",
            value=_percent(analysis.drawdown.current_drawdown),
            source_type=historical,
        ),
        EvidenceKey.EFFECTIVE_POSITIONS: OfficerEvidence(
            key=EvidenceKey.EFFECTIVE_POSITIONS,
            label="Effective number of positions",
            value=f"{concentration.effective_positions:.2f}",
            source_type=historical,
        ),
        EvidenceKey.LARGEST_POSITION: OfficerEvidence(
            key=EvidenceKey.LARGEST_POSITION,
            label="Largest portfolio weight",
            value=f"{concentration.largest_position_ticker} · {_percent(concentration.largest_position)}",
            source_type=historical,
        ),
        EvidenceKey.TOP_THREE_CONCENTRATION: OfficerEvidence(
            key=EvidenceKey.TOP_THREE_CONCENTRATION,
            label="Top three concentration",
            value=_percent(concentration.top_3_concentration),
            source_type=historical,
        ),
        EvidenceKey.LARGEST_RISK_CONTRIBUTOR: OfficerEvidence(
            key=EvidenceKey.LARGEST_RISK_CONTRIBUTOR,
            label="Largest volatility risk contributor",
            value=f"{largest_risk.ticker} · {_percent(largest_risk.risk_contribution)}",
            source_type=historical,
        ),
        EvidenceKey.RISK_FLAGS: OfficerEvidence(
            key=EvidenceKey.RISK_FLAGS,
            label="Deterministic risk flags",
            value=(
                ", ".join(flag.title for flag in analysis.risk_flags)
                or "None triggered"
            ),
            source_type=historical,
        ),
    }

    if highest_correlation is not None:
        catalog[EvidenceKey.HIGHEST_CORRELATION] = OfficerEvidence(
            key=EvidenceKey.HIGHEST_CORRELATION,
            label="Highest pairwise correlation",
            value=(
                f"{highest_correlation.asset_1} / {highest_correlation.asset_2} · "
                f"{highest_correlation.correlation:.2f}"
            ),
            source_type=historical,
        )

    factor = analysis.factor_exposure
    if factor.available and factor.market_beta is not None:
        catalog[EvidenceKey.MARKET_BETA] = OfficerEvidence(
            key=EvidenceKey.MARKET_BETA,
            label=f"Market beta versus {factor.benchmark_ticker}",
            value=f"{factor.market_beta:.2f}",
            source_type=historical,
        )
    if factor.available and factor.alpha_annualized is not None:
        catalog[EvidenceKey.FACTOR_ALPHA] = OfficerEvidence(
            key=EvidenceKey.FACTOR_ALPHA,
            label="Annualized regression alpha",
            value=_percent(factor.alpha_annualized),
            source_type=historical,
        )
    if factor.available and factor.r_squared is not None:
        catalog[EvidenceKey.FACTOR_R_SQUARED] = OfficerEvidence(
            key=EvidenceKey.FACTOR_R_SQUARED,
            label="Market-factor regression R-squared",
            value=_percent(factor.r_squared),
            source_type=historical,
        )
    if factor.available and factor.idiosyncratic_volatility is not None:
        catalog[EvidenceKey.IDIOSYNCRATIC_VOLATILITY] = OfficerEvidence(
            key=EvidenceKey.IDIOSYNCRATIC_VOLATILITY,
            label="Annualized idiosyncratic volatility",
            value=_percent(factor.idiosyncratic_volatility),
            source_type=historical,
        )

    if stress_test is not None:
        scenario_source = "hypothetical_scenario_result"
        catalog[EvidenceKey.STRESS_PORTFOLIO_RETURN] = OfficerEvidence(
            key=EvidenceKey.STRESS_PORTFOLIO_RETURN,
            label="Estimated portfolio stress return",
            value=_percent(stress_test.estimated_portfolio_return),
            source_type=scenario_source,
        )
        catalog[EvidenceKey.STRESS_DOLLAR_PNL] = OfficerEvidence(
            key=EvidenceKey.STRESS_DOLLAR_PNL,
            label="Estimated stress P&L",
            value=_money(stress_test.estimated_dollar_pnl),
            source_type=scenario_source,
        )
        top_stress = min(
            stress_test.asset_contributions,
            key=lambda item: item.portfolio_contribution,
        )
        catalog[EvidenceKey.STRESS_TOP_CONTRIBUTOR] = OfficerEvidence(
            key=EvidenceKey.STRESS_TOP_CONTRIBUTOR,
            label="Largest loss contributor",
            value=f"{top_stress.ticker} · {_percent(top_stress.portfolio_contribution)}",
            source_type=scenario_source,
        )
    return catalog


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _money(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"
