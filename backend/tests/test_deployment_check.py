"""Deployment probes run against an in-process API, never Yahoo or an LLM."""

import argparse
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
