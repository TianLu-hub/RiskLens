"""Phase 3 AI boundary and orchestration tests."""

from __future__ import annotations

from typing import Literal

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AuthenticationError, RateLimitError
from pydantic import ValidationError

from app.api.ai import get_configured_risk_officer_ai
from app.ai.deterministic_officer import DeterministicRiskOfficer
from app.ai.officer import _classify_provider_error
from app.ai.scenario_parser import ScenarioInterpretationError
from app.main import app
from app.models.ai import (
    EvidenceKey,
    OfficerFindingDraft,
    OfficerIntent,
    OfficerNarrativeDraft,
    ParsedRiskIntent,
    ParsedTickerShock,
)


class FakeRiskOfficerAI:
    model = "test-structured-model"
    narrative_source = "openai_structured_output"

    def __init__(self, mode: Literal["analysis", "stress"] = "analysis") -> None:
        self.mode = mode

    def parse_intent(self, question: str, tickers: list[str]) -> ParsedRiskIntent:
        assert question
        assert tickers == ["AAPL", "MSFT", "NVDA", "SPY", "TLT"]
        if self.mode == "stress":
            return ParsedRiskIntent(
                intent=OfficerIntent.STRESS_SCENARIO,
                scenario_name="AI translated scenario",
                market_shock=-0.10,
                tech_shock=-0.15,
                rates_shock_bps=100,
                ticker_shocks=[ParsedTickerShock(ticker="NVDA", shock=-0.30)],
            )
        return ParsedRiskIntent(
            intent=OfficerIntent.PORTFOLIO_ANALYSIS,
            scenario_name=None,
            market_shock=None,
            tech_shock=None,
            rates_shock_bps=None,
            ticker_shocks=[],
        )

    def create_narrative(self, question, analysis, stress_test):
        evidence_keys = (
            [EvidenceKey.STRESS_PORTFOLIO_RETURN, EvidenceKey.STRESS_TOP_CONTRIBUTOR]
            if stress_test is not None
            else [EvidenceKey.LARGEST_RISK_CONTRIBUTOR, EvidenceKey.HIGHEST_CORRELATION]
        )
        return OfficerNarrativeDraft(
            headline="Technology exposure is the dominant vulnerability",
            summary="Equity positions share a common risk channel while bonds provide partial diversification.",
            findings=[
                OfficerFindingDraft(
                    title="Concentrated volatility contribution",
                    explanation="The leading equity exposures account for most of the portfolio risk budget.",
                    evidence_keys=evidence_keys,
                )
            ],
            limitations=["Factor exposure is unavailable in the current analysis."],
        )


def _request_payload(question: str) -> dict:
    return {
        "question": question,
        "positions": [
            {"ticker": "AAPL", "weight": 0.20},
            {"ticker": "MSFT", "weight": 0.20},
            {"ticker": "NVDA", "weight": 0.15},
            {"ticker": "SPY", "weight": 0.25},
            {"ticker": "TLT", "weight": 0.20},
        ],
        "portfolio_value": 100_000,
        "analysis": {
            "metrics": {
                "annualized_return": 0.14,
                "annualized_volatility": 0.18,
                "sharpe_ratio": 0.56,
                "var": 0.019,
                "cvar": 0.029,
                "confidence_level": 0.95,
                "var_horizon_days": 1,
                "risk_free_rate": 0.04,
            },
            "drawdown": {"current_drawdown": -0.03, "max_drawdown": -0.17},
            "correlation": {
                "highest_correlations": [
                    {"asset_1": "MSFT", "asset_2": "SPY", "correlation": 0.82}
                ]
            },
            "risk_contributions": [
                {
                    "ticker": "AAPL",
                    "weight": 0.20,
                    "marginal_risk": 0.18,
                    "absolute_risk_contribution": 0.036,
                    "risk_contribution": 0.20,
                },
                {
                    "ticker": "MSFT",
                    "weight": 0.20,
                    "marginal_risk": 0.19,
                    "absolute_risk_contribution": 0.038,
                    "risk_contribution": 0.21,
                },
                {
                    "ticker": "NVDA",
                    "weight": 0.15,
                    "marginal_risk": 0.34,
                    "absolute_risk_contribution": 0.051,
                    "risk_contribution": 0.28,
                },
                {
                    "ticker": "SPY",
                    "weight": 0.25,
                    "marginal_risk": 0.22,
                    "absolute_risk_contribution": 0.055,
                    "risk_contribution": 0.30,
                },
                {
                    "ticker": "TLT",
                    "weight": 0.20,
                    "marginal_risk": 0.01,
                    "absolute_risk_contribution": 0.002,
                    "risk_contribution": 0.01,
                },
            ],
            "concentration": {
                "hhi": 0.205,
                "effective_positions": 4.878,
                "largest_position": 0.25,
                "largest_position_ticker": "SPY",
                "top_3_concentration": 0.65,
                "position_count": 5,
            },
            "factor_exposure": {
                "model": "CAPM_SPY",
                "benchmark_ticker": "SPY",
                "benchmark_source": "Synthetic Test Data",
                "available": True,
                "alpha_annualized": 0.02,
                "market_beta": 0.93,
                "smb_beta": None,
                "hml_beta": None,
                "r_squared": 0.81,
                "idiosyncratic_volatility": 0.07,
                "observations": 519,
                "rolling_window_days": 60,
                "rolling_beta": [],
                "methodology": "Deterministic test regression.",
                "unavailable_reason": None,
            },
            "risk_flags": [
                {
                    "code": "HIGH_CORRELATION",
                    "severity": "medium",
                    "title": "High correlation",
                    "detail": "Maximum pairwise correlation is elevated.",
                }
            ],
            "data_quality": {
                "source": "Synthetic Test Data",
                "observations": 519,
                "start_date": "2023-01-03",
                "end_date": "2024-12-27",
                "requested_lookback_years": 3,
                "warnings": [],
            },
        },
    }


def test_risk_officer_explains_calculated_context() -> None:
    app.dependency_overrides[get_configured_risk_officer_ai] = (
        lambda: FakeRiskOfficerAI()
    )
    response = TestClient(app).post(
        "/ai/risk-officer", json=_request_payload("Diagnose this portfolio")
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "portfolio_analysis"
    assert payload["stress_test"] is None
    assert payload["narrative_source"] == "openai_structured_output"
    evidence = payload["findings"][0]["evidence"]
    assert evidence[0]["value"] == "SPY · 30.00%"
    assert evidence[1]["source_type"] == "observed_historical_statistic"


def test_natural_language_scenario_runs_python_stress_engine() -> None:
    app.dependency_overrides[get_configured_risk_officer_ai] = (
        lambda: FakeRiskOfficerAI("stress")
    )
    response = TestClient(app).post(
        "/ai/risk-officer",
        json=_request_payload(
            "What if tech drops and rates rise under the supplied scenario?"
        ),
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "stress_scenario"
    assert payload["parsed_scenario"]["tech_shock"] == -0.15
    assert payload["stress_test"]["estimated_portfolio_return"] == pytest.approx(
        -0.21325
    )
    assert payload["stress_test"]["estimated_dollar_pnl"] == pytest.approx(-21_325)
    assert sum(
        item["portfolio_contribution"]
        for item in payload["stress_test"]["asset_contributions"]
    ) == pytest.approx(payload["stress_test"]["estimated_portfolio_return"])


def test_llm_narrative_contract_rejects_numeric_prose() -> None:
    with pytest.raises(ValidationError):
        OfficerNarrativeDraft(
            headline="Volatility is 18 percent",
            summary="Numeric claims are rejected.",
            findings=[
                OfficerFindingDraft(
                    title="Tail risk",
                    explanation="Expected shortfall is elevated.",
                    evidence_keys=[EvidenceKey.CVAR],
                )
            ],
            limitations=["Factor exposure is unavailable."],
        )


def test_risk_officer_reports_missing_backend_key(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = TestClient(app).post(
        "/ai/risk-officer", json=_request_payload("Diagnose this portfolio")
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AI_NOT_CONFIGURED"


def test_deterministic_officer_requires_no_api_key(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = TestClient(app).post(
        "/ai/risk-officer", json=_request_payload("Diagnose this portfolio")
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "portfolio_analysis"
    assert payload["narrative_source"] == "deterministic_rule_engine"
    assert payload["model"] == "risklens-deterministic-officer"


def test_deterministic_english_scenario_runs_python_engine(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    response = TestClient(app).post(
        "/ai/risk-officer",
        json=_request_payload("What happens if tech drops 15% and rates rise 100 bps?"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["parsed_scenario"]["tech_shock"] == pytest.approx(-0.15)
    assert payload["parsed_scenario"]["rates_shock_bps"] == pytest.approx(100)
    assert payload["stress_test"]["estimated_portfolio_return"] == pytest.approx(
        -0.12575
    )


def test_deterministic_chinese_scenario_parser() -> None:
    parsed = DeterministicRiskOfficer().parse_intent(
        "如果科技下跌15%，利率上升100个基点会怎样？",
        ["AAPL", "MSFT", "NVDA", "SPY", "TLT"],
    )

    assert parsed.intent is OfficerIntent.STRESS_SCENARIO
    assert parsed.tech_shock == pytest.approx(-0.15)
    assert parsed.rates_shock_bps == pytest.approx(100)


def test_deterministic_ticker_and_market_scenario_parser() -> None:
    parsed = DeterministicRiskOfficer().parse_intent(
        "What if NVDA drops 30% and the overall market falls 10%?",
        ["AAPL", "MSFT", "NVDA", "SPY", "TLT"],
    )

    assert parsed.intent is OfficerIntent.STRESS_SCENARIO
    assert parsed.market_shock == pytest.approx(-0.10)
    assert len(parsed.ticker_shocks) == 1
    assert parsed.ticker_shocks[0].ticker == "NVDA"
    assert parsed.ticker_shocks[0].shock == pytest.approx(-0.30)


@pytest.mark.parametrize(
    "question,tickers,expected",
    [
        ("NVDA drops 30%", ["A", "NVDA"], {"NVDA": -0.30}),
        ("30% drop SPY", ["S", "SPY"], {"SPY": -0.30}),
        ("BRK-B drops 10%", ["B", "BRK", "BRK-B"], {"BRK-B": -0.10}),
        ("10% drop BRK-B", ["B", "BRK", "BRK-B"], {"BRK-B": -0.10}),
        ("10% drop BRK.B", ["B", "BRK", "BRK.B"], {"BRK.B": -0.10}),
        ("10% drop ABC-2", ["ABC", "ABC-2"], {"ABC-2": -0.10}),
        ("NVDA-30%", ["A", "NVDA"], {"NVDA": -0.30}),
        ("如果NVDA下跌30%会怎样？", ["A", "NVDA"], {"NVDA": -0.30}),
        ("A drops 10% and NVDA drops 30%", ["A", "NVDA"], {"A": -0.10, "NVDA": -0.30}),
        ("10% drop A. 30% drop NVDA.", ["A", "NVDA"], {"A": -0.10, "NVDA": -0.30}),
        ("$NVDA drops 30%", ["A", "NVDA"], {"NVDA": -0.30}),
    ],
)
def test_scenario_subjects_match_whole_identifiers(question, tickers, expected):
    parsed = DeterministicRiskOfficer().parse_intent(question, tickers)
    assert parsed.intent is OfficerIntent.STRESS_SCENARIO
    assert {item.ticker: item.shock for item in parsed.ticker_shocks} == expected


@pytest.mark.parametrize(
    "question",
    [
        "What if supermarket drops 10%?",
        "What if biotech drops 10%?",
        "What if corporate rises 100 bps?",
        "What if NVDA.US drops 10%?",
        "What if 10% drop NVDA.US?",
        "What if XNVDA drops 10%?",
    ],
)
def test_subject_substrings_do_not_trigger_stress_computation(monkeypatch, question):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")

    def unexpected_call(*args, **kwargs):
        pytest.fail("Unmatched subjects must not reach stress computation or narrative")

    monkeypatch.setattr("app.ai.officer.run_stress_test", unexpected_call)
    monkeypatch.setattr(DeterministicRiskOfficer, "create_narrative", unexpected_call)
    response = TestClient(app).post("/ai/risk-officer", json=_request_payload(question))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_AI_SCENARIO"


def test_ticker_substring_cannot_add_an_unrequested_loss(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    payload = _request_payload("What if NVDA drops 30%?")
    payload["positions"][0]["ticker"] = "A"
    payload["analysis"]["risk_contributions"][0]["ticker"] = "A"
    response = TestClient(app).post("/ai/risk-officer", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["parsed_scenario"]["ticker_shocks"] == [
        {"ticker": "NVDA", "shock": -0.30}
    ]
    assets = {
        item["ticker"]: item for item in result["stress_test"]["asset_contributions"]
    }
    assert assets["A"]["estimated_asset_return"] == 0
    assert assets["NVDA"]["estimated_asset_return"] == pytest.approx(-0.30)
    assert result["stress_test"]["estimated_portfolio_return"] == pytest.approx(-0.045)


@pytest.mark.parametrize(
    "question",
    [
        "Market-10%, tech+15%, rates+100bps",
        "10% drop market. 15% rise technology. 100 bps rise rates.",
        "如果大盘下跌10%，科技上涨15%，利率上升100个基点",
    ],
)
def test_subject_boundaries_preserve_supported_factor_scenarios(question):
    parsed = DeterministicRiskOfficer().parse_intent(question, ["SPY"])
    assert parsed.market_shock == pytest.approx(-0.10)
    assert parsed.tech_shock == pytest.approx(0.15)
    assert parsed.rates_shock_bps == pytest.approx(100)
    assert parsed.ticker_shocks == []


@pytest.mark.parametrize(
    "question",
    [
        "What if NVDA drops 150%?",
        "NVDA +100.01%",
        "如果NVDA下跌150%会怎样？",
        "NVDA上涨150%",
        "Tech drops 15% and NVDA drops 150%",
        "NVDA -" + "9" * 400 + "%",
        "Tech drops 150%",
        "Market +150%",
        "Rates rise 1001 bps",
    ],
)
def test_out_of_range_scenarios_return_422_without_computation(monkeypatch, question):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")

    def unexpected_call(*args, **kwargs):
        pytest.fail(
            "Invalid scenario must not reach stress computation or narrative generation"
        )

    monkeypatch.setattr("app.ai.officer.run_stress_test", unexpected_call)
    monkeypatch.setattr(DeterministicRiskOfficer, "create_narrative", unexpected_call)
    with pytest.raises(ScenarioInterpretationError, match="outside.*bounds"):
        DeterministicRiskOfficer().parse_intent(question, ["NVDA"])

    response = TestClient(app, raise_server_exceptions=False).post(
        "/ai/risk-officer", json=_request_payload(question)
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "INVALID_AI_SCENARIO",
        "message": "A parsed shock is outside the supported scenario bounds.",
    }


@pytest.mark.parametrize("shock", [-100, 0, 100])
def test_ticker_shock_bounds_are_inclusive(monkeypatch, shock):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    response = TestClient(app).post(
        "/ai/risk-officer",
        json=_request_payload(f"Market -10% and NVDA {shock:+}%"),
    )
    assert response.status_code == 200
    result = response.json()
    assert result["parsed_scenario"]["ticker_shocks"] == [
        {"ticker": "NVDA", "shock": shock / 100}
    ]
    asset = next(
        item
        for item in result["stress_test"]["asset_contributions"]
        if item["ticker"] == "NVDA"
    )
    assert asset["estimated_asset_return"] == pytest.approx(shock / 100)
    assert asset["portfolio_contribution"] == pytest.approx(0.15 * shock / 100)


@pytest.mark.parametrize(
    "question",
    [
        "Tech drops 15% and tech rises 20%",
        "Tech rises 20% and tech drops 15%",
        "NVDA -10%, NVDA -30%",
        "NVDA +0%, NVDA -30%",
        "Overall market drops 10%, market drops 20%",
        "Tech -15%, technology drops 20%",
        "Tech drops 15%, 20% fall tech",
        "Rates rise 100 bps and interest rates fall 50 bps",
        "科技下跌15%，科技上涨20%",
        "利率上升100个基点，利率下降50个基点",
        "NVDA下跌10%，NVDA下跌30%",
    ],
)
def test_conflicting_scenario_shocks_are_rejected(monkeypatch, question):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")

    def unexpected_call(*args, **kwargs):
        pytest.fail("Conflicting shocks must not reach computation or explanation")

    monkeypatch.setattr("app.ai.officer.run_stress_test", unexpected_call)
    monkeypatch.setattr(DeterministicRiskOfficer, "create_narrative", unexpected_call)
    with pytest.raises(ScenarioInterpretationError, match="Conflicting shocks"):
        DeterministicRiskOfficer().parse_intent(question, ["NVDA"])
    response = TestClient(app).post("/ai/risk-officer", json=_request_payload(question))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_AI_SCENARIO"
    assert "separate scenarios" in response.json()["detail"]["message"]


@pytest.mark.parametrize(
    "question",
    [
        "Tech drops 15%, technology -15%, rates +100 bps, NVDA -30%",
        "科技下跌15%，科技板块下跌15%，利率上升100个基点，NVDA下跌30%",
    ],
)
def test_repeated_equivalent_shocks_and_distinct_factors_are_preserved(
    monkeypatch, question
):
    monkeypatch.setenv("AI_PROVIDER", "deterministic")
    response = TestClient(app).post("/ai/risk-officer", json=_request_payload(question))
    assert response.status_code == 200
    scenario = response.json()["parsed_scenario"]
    assert scenario["tech_shock"] == pytest.approx(-0.15)
    assert scenario["rates_shock_bps"] == pytest.approx(100)
    assert scenario["ticker_shocks"] == [{"ticker": "NVDA", "shock": -0.30}]
    assets = response.json()["stress_test"]["asset_contributions"]
    assert sum(item["portfolio_contribution"] for item in assets) == pytest.approx(
        response.json()["stress_test"]["estimated_portfolio_return"]
    )


@pytest.mark.parametrize(
    "provider_code", ["insufficient_quota", "credit_balance_exhausted"]
)
def test_provider_error_reports_missing_api_quota_safely(provider_code: str) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request)
    provider_error = RateLimitError(
        "quota unavailable",
        response=response,
        body={"code": provider_code},
    )

    error = _classify_provider_error(provider_error, stage="intent_parsing")

    assert error.code == "AI_QUOTA_EXCEEDED"
    assert error.stage == "intent_parsing"
    assert "API key" not in error.public_message


def test_provider_error_reports_invalid_key_without_echoing_it() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(401, request=request)
    provider_error = AuthenticationError(
        "invalid secret",
        response=response,
        body={"code": "invalid_api_key"},
    )

    error = _classify_provider_error(provider_error, stage="narrative_generation")

    assert error.code == "AI_AUTHENTICATION_FAILED"
    assert error.stage == "narrative_generation"
    assert "invalid secret" not in error.public_message
