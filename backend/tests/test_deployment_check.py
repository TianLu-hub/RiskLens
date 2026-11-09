"""Deployment probes run against an in-process API, never Yahoo or an LLM."""

import argparse
import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import (
    MarketDataProvider,
    PriceHistory,
    get_market_data_provider,
)
from app.main import app
from scripts.check_deployment import (
    CheckFailed,
    check_deployment,
    main,
    origin_url,
    positive_timeout,
)

ORIGIN = "http://localhost:3000"


@pytest.fixture
def probe_api(asset_returns):
    provider = Mock(spec=MarketDataProvider)
    returns = asset_returns.assign(NVDA=asset_returns.AAPL, SPY=asset_returns.MSFT)
    provider.get_adjusted_prices.return_value = PriceHistory(
        prices=100 * (1 + returns).cumprod(),
        source="Synthetic Test Data",
        warnings=[],
    )
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_default_checks_do_not_fetch_prices_or_call_ai(probe_api):
    client, provider = probe_api
    paths = []
    client.event_hooks["request"] = [lambda request: paths.append(request.url.path)]
    messages = check_deployment(client, ORIGIN)
    assert len([message for message in messages if message.startswith("PASS")]) == 3
    assert messages[-1].startswith("SKIP market analysis")
    assert paths == ["/health", "/portfolio/stress-test", "/portfolio/stress-test"]
    provider.get_adjusted_prices.assert_not_called()


def test_optional_analysis_validates_real_api_contract(probe_api):
    client, provider = probe_api
    messages = check_deployment(client, ORIGIN, include_market_data=True)
    assert messages[-1] == "PASS analysis: 7 return observations"
    provider.get_adjusted_prices.assert_called_once()


def test_wrong_browser_origin_fails_even_when_health_is_ok(probe_api):
    client, provider = probe_api
    with pytest.raises(CheckFailed, match="CORS_ORIGINS"):
        check_deployment(client, "https://not-allowed.example")
    provider.get_adjusted_prices.assert_not_called()


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("html", "not valid RiskLens JSON"),
        ("wrong_service", "Unexpected service"),
        ("preflight_headers", "Preflight does not allow"),
        ("preflight_method", "Preflight does not allow"),
        ("stress_cors", "Browser access blocked"),
        ("stress_schema", "not valid RiskLens JSON"),
        ("market_outage", "market analysis: HTTP 503"),
        ("redirect", "health: HTTP 307"),
    ],
)
def test_diagnostics_reject_partial_or_misconfigured_deployments(
    probe_api, failure, expected
):
    api, _ = probe_api

    def handler(request):
        response = api.request(
            request.method,
            request.url.path,
            headers=request.headers,
            content=request.content,
        )
        if request.url.path == "/health":
            if failure == "html":
                return httpx.Response(200, text="<html>Login page</html>")
            if failure == "redirect":
                return httpx.Response(307, headers={"Location": "https://example.com"})
            if failure == "wrong_service":
                return httpx.Response(
                    200, json={"status": "ok", "service": "other-app", "version": "1"}
                )
        if request.method == "OPTIONS":
            if failure == "preflight_headers":
                response.headers["access-control-allow-headers"] = "content-type"
            if failure == "preflight_method":
                response.headers["access-control-allow-methods"] = "GET"
        if request.method == "POST" and request.url.path == "/portfolio/stress-test":
            if failure == "stress_cors":
                del response.headers["access-control-allow-origin"]
            if failure == "stress_schema":
                return httpx.Response(200, json={}, headers=response.headers)
        if request.url.path == "/portfolio/analyze" and failure == "market_outage":
            return httpx.Response(503, text="private upstream diagnostics")
        return httpx.Response(
            response.status_code, headers=response.headers, content=response.content
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.example"
        ) as client,
        pytest.raises(CheckFailed, match=expected),
    ):
        check_deployment(client, ORIGIN, include_market_data=True)


def test_cli_connection_failure_has_nonzero_exit_without_raw_error(monkeypatch, capsys):
    def fail(request):
        raise httpx.ConnectError("sensitive proxy diagnostic", request=request)

    client = httpx.Client(
        transport=httpx.MockTransport(fail), base_url="https://api.example"
    )
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    assert main([]) == 1
    output = capsys.readouterr().out
    assert "FAIL health: connection/TLS/timeout failure" in output
    assert "sensitive" not in output


def test_cli_success_returns_zero(probe_api, monkeypatch, capsys):
    client, _ = probe_api
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    assert main([]) == 0
    assert "PASS stress" in capsys.readouterr().out


@pytest.mark.parametrize("include_market_data", [False, True])
def test_json_report_records_scope_and_utc_times(
    probe_api, monkeypatch, capsys, include_market_data
):
    client, provider = probe_api
    sha = "abcdef01" * 5
    monkeypatch.setenv("RISKLENS_REVISION", sha)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    args = ["--json", "--expected-revision", sha.upper()]
    if include_market_data:
        args.append("--include-market-data")
    assert main(args) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == ""
    assert report["schema_version"] == 1
    assert report["status"] == "passed"
    assert report["error"] is None
    assert report["api_url"] == "http://127.0.0.1:8000"
    assert report["origin"] == ORIGIN
    assert report["requested_checks"] == {
        "market_data": include_market_data,
        "var_backtest": False,
        "expected_revision": sha,
    }
    started = datetime.fromisoformat(report["started_at"])
    finished = datetime.fromisoformat(report["finished_at"])
    assert started.utcoffset() == finished.utcoffset() == timedelta(0)
    assert started <= finished
    assert report["messages"][0].startswith("PASS health")
    assert any(m.startswith("PASS revision") for m in report["messages"])
    assert report["messages"][-1].startswith(
        "PASS analysis" if include_market_data else "SKIP market analysis"
    )
    assert provider.get_adjusted_prices.call_count == int(include_market_data)


@pytest.mark.parametrize(
    "stage,path,method,failure,completed",
    [
        ("health", "/health", "GET", "http", 0),
        ("health", "/health", "GET", "timeout", 0),
        ("CORS preflight", "/portfolio/stress-test", "OPTIONS", "cors", 1),
        ("stress endpoint", "/portfolio/stress-test", "POST", "schema", 2),
        ("stress endpoint", "/portfolio/stress-test", "POST", "result", 2),
        ("market analysis", "/portfolio/analyze", "POST", "http", 3),
        ("VaR backtest", "/portfolio/var-backtest", "POST", "http", 4),
    ],
)
def test_json_failure_retains_progress_without_leaking_diagnostics(
    probe_api, monkeypatch, capsys, stage, path, method, failure, completed
):
    api, _ = probe_api
    private = "private-upstream-diagnostic-do-not-print"

    def handler(request):
        target = request.url.path == path and request.method == method
        if target and failure == "http":
            return httpx.Response(503, text=private, headers={"x-private": private})
        if target and failure == "timeout":
            raise httpx.ReadTimeout(private, request=request)
        response = api.request(
            request.method,
            request.url.path,
            headers=request.headers,
            content=request.content,
        )
        if target:
            if failure == "cors":
                del response.headers["access-control-allow-origin"]
            elif failure == "schema":
                return httpx.Response(200, text=private, headers=response.headers)
            elif failure == "result":
                data = response.json()
                data["scenario_name"] = private
                return httpx.Response(200, json=data, headers=response.headers)
        return httpx.Response(
            response.status_code, headers=response.headers, content=response.content
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    )
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    assert (
        main(
            [
                "--json",
                "--api-url",
                "https://api.example/",
                "--include-market-data",
                "--include-var-backtest",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert private not in captured.out + captured.err
    report = json.loads(captured.out)
    assert report["status"] == "failed"
    assert report["api_url"] == "https://api.example"
    assert report["error"]["stage"] == stage
    assert len(report["messages"]) == completed
    assert report["requested_checks"] == {
        "market_data": True,
        "var_backtest": True,
        "expected_revision": None,
    }
    assert all(message.startswith("PASS") for message in report["messages"])


def test_json_revision_failure_does_not_claim_release_passed(
    probe_api, monkeypatch, capsys
):
    client, provider = probe_api
    monkeypatch.delenv("RISKLENS_REVISION", raising=False)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    assert main(["--json", "--expected-revision", "a" * 40]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["error"]["stage"] == "release revision"
    assert len(report["messages"]) == 1
    assert report["messages"][0].startswith("PASS health")
    provider.get_adjusted_prices.assert_not_called()


def test_json_invalid_arguments_keep_standard_usage_error(monkeypatch, capsys):
    client = Mock()
    monkeypatch.setattr(httpx, "Client", client)
    with pytest.raises(SystemExit) as exc:
        main(["--json", "--timeout", "0"])
    assert exc.value.code == 2
    assert capsys.readouterr().out == ""
    client.assert_not_called()


@pytest.mark.parametrize(
    "path,value",
    [
        (("estimated_portfolio_return",), 0.16),
        (("estimated_portfolio_return",), float("nan")),
        (("estimated_dollar_pnl",), float("inf")),
        (("estimated_dollar_pnl",), -1),
        (("portfolio_value_before",), 1),
        (("portfolio_value_after",), None),
        (("scenario_name",), "private-upstream-diagnostic"),
        (("historical_data_used",), True),
        (("historical_data_used",), "false"),
        (("scenario_inputs", "rates_shock_bps"), -100),
        (("scenario_inputs", "market_shock"), -0.1),
        (("scenario_inputs", "ticker_shocks"), {"TLT": -0.16}),
        (("asset_contributions",), []),
        (("asset_contributions", 0, "ticker"), "SPY"),
        (("asset_contributions", 0, "weight"), True),
        (("asset_contributions", 0, "portfolio_contribution"), 0.16),
        (("asset_contributions", 0, "position_value_after"), 100_000),
        (("asset_contributions", 0, "factor_shocks"), {"interest_rates": 0.16}),
        (("factor_contributions",), []),
        (("factor_contributions", 0, "factor"), "technology"),
        (("factor_contributions", 0, "portfolio_contribution"), 0.16),
        (("factor_contributions", 0, "estimated_dollar_pnl"), "-16000"),
        (("assumptions",), []),
    ],
)
def test_stress_probe_rejects_corrupted_results(probe_api, path, value):
    api, provider = probe_api

    def handler(request):
        response = api.request(
            request.method,
            request.url.path,
            headers=request.headers,
            content=request.content,
        )
        if request.method == "POST":
            payload = response.json()
            target = payload
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            # Explicit serialization also exercises non-finite provider JSON.
            return httpx.Response(
                200, content=json.dumps(payload), headers=response.headers
            )
        return httpx.Response(
            response.status_code, content=response.content, headers=response.headers
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.example"
        ) as client,
        pytest.raises(CheckFailed) as error,
    ):
        check_deployment(client, ORIGIN)
    assert "private-upstream-diagnostic" not in str(error.value)
    provider.get_adjusted_prices.assert_not_called()


@pytest.mark.parametrize("change", ["source", "duration", "duplicate"])
def test_stress_probe_rejects_incorrect_fallback_disclosure(probe_api, change):
    api, _ = probe_api

    def handler(request):
        response = api.request(
            request.method,
            request.url.path,
            headers=request.headers,
            content=request.content,
        )
        if request.method == "POST":
            payload = response.json()
            duration = next(
                a for a in payload["assumptions"] if a["id"] == "duration_TLT"
            )
            if change == "source":
                duration["source_type"] = "user_input"
            elif change == "duration":
                duration["value"] = "15.0 years"
            else:
                payload["assumptions"].append(duration.copy())
            return httpx.Response(200, json=payload, headers=response.headers)
        return httpx.Response(
            response.status_code, content=response.content, headers=response.headers
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.example"
        ) as client,
        pytest.raises(CheckFailed, match="fallback disclosure"),
    ):
        check_deployment(client, ORIGIN)


@pytest.mark.parametrize(
    "value",
    [
        "ftp://host",
        "localhost:8000",
        "https://user:secret@host",
        "https://host/path",
        "https://host?key=secret",
        "https://host#fragment",
    ],
)
def test_invalid_origins_are_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        origin_url(value)


def test_trailing_slash_is_normalized():
    assert origin_url("https://api.example/") == "https://api.example"


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_timeouts_are_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        positive_timeout(value)
