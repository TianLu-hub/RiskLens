"""Opt-in VaR/Kupiec deployment probes use synthetic prices and in-process HTTP."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import Mock

import httpx
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.market_data import (
    MarketDataProvider,
    PriceHistory,
    get_market_data_provider,
)
from app.data.provenance import AssetCoverage, MarketDataProvenance
from app.main import app
from scripts.check_deployment import CheckFailed, check_deployment, main

ORIGIN = "http://localhost:3000"
VAR_PATH = "/portfolio/var-backtest"
PRIVATE_DIAGNOSTIC = "private-provider-diagnostic-do-not-print"
POSITIONS = [
    {"ticker": "AAPL", "weight": 0.20},
    {"ticker": "MSFT", "weight": 0.20},
    {"ticker": "NVDA", "weight": 0.15},
    {"ticker": "SPY", "weight": 0.25},
    {"ticker": "TLT", "weight": 0.20},
]


@pytest.fixture
def var_probe_api(monkeypatch):
    index = pd.bdate_range("2024-01-02", periods=320)
    time = np.arange(len(index))
    prices = pd.DataFrame(
        {
            position["ticker"]: 100
            * np.cumprod(1 + 0.0004 + 0.008 * np.sin(time / (7 + offset)))
            for offset, position in enumerate(POSITIONS)
        },
        index=index,
    )
    provider = Mock(spec=MarketDataProvider)
    provider.get_adjusted_prices.return_value = PriceHistory(
        prices=prices,
        source="Synthetic Test Data",
        warnings=[],
        provenance=MarketDataProvenance(
            data_type="synthetic",
            fetched_at=datetime(2025, 6, 1, 12, tzinfo=UTC),
            cache_hit=False,
            cache_ttl_seconds=900,
            price_basis="adjusted_close",
            price_start_date=index[0].date().isoformat(),
            price_end_date=index[-1].date().isoformat(),
            raw_price_rows=len(prices),
            aligned_price_rows=len(prices),
            dropped_price_rows=0,
            forward_fill_limit=3,
            assets=[
                AssetCoverage(
                    ticker=ticker,
                    observed_prices=len(prices),
                    missing_prices=0,
                    filled_prices=0,
                    first_observed_date=index[0].date().isoformat(),
                    last_observed_date=index[-1].date().isoformat(),
                )
                for ticker in prices.columns
            ],
        ),
    )
    monkeypatch.setattr(
        "app.data.market_data.yf.download",
        Mock(side_effect=AssertionError("Deployment-check tests must not call Yahoo")),
    )
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_market_data_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            yield client, provider
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def _proxy_response(api: TestClient, request: httpx.Request) -> httpx.Response:
    response = api.request(
        request.method,
        request.url.path,
        headers=request.headers,
        content=request.content,
    )
    return httpx.Response(
        response.status_code, headers=response.headers, content=response.content
    )


def test_default_probe_still_avoids_history_and_ai(var_probe_api):
    api, provider = var_probe_api
    requests = []
    api.event_hooks["request"] = [lambda request: requests.append(request)]
    check_deployment(api, ORIGIN)
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/health"),
        ("OPTIONS", "/portfolio/stress-test"),
        ("POST", "/portfolio/stress-test"),
    ]
    provider.get_adjusted_prices.assert_not_called()


def test_iso_timestamp_provenance_passes_strict_json_validation(var_probe_api):
    api, provider = var_probe_api
    inspected = []

    def handler(request):
        response = _proxy_response(api, request)
        if request.method == "POST" and request.url.path == VAR_PATH:
            inspected.append(response.json()["data_quality"]["provenance"])
        return response

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    ) as client:
        check_deployment(client, ORIGIN, include_var_backtest=True)
    assert inspected[0]["fetched_at"] == "2025-06-01T12:00:00Z"
    assert inspected[0]["cache_hit"] is False
    assert inspected[0] == (
        provider.get_adjusted_prices.return_value.provenance.model_dump(mode="json")
    )


@pytest.mark.parametrize(
    ("include_market_data", "include_var_backtest"),
    [(False, True), (True, False), (True, True)],
)
def test_history_probes_are_independently_opted_in(
    var_probe_api,
    include_market_data,
    include_var_backtest,
):
    api, provider = var_probe_api
    requests = []
    api.event_hooks["request"] = [lambda request: requests.append(request)]
    messages = check_deployment(
        api,
        ORIGIN,
        include_market_data=include_market_data,
        include_var_backtest=include_var_backtest,
    )
    paths = [(request.method, request.url.path) for request in requests]
    assert (("POST", "/portfolio/analyze") in paths) is include_market_data
    assert (("POST", VAR_PATH) in paths) is include_var_backtest
    assert (("OPTIONS", VAR_PATH) in paths) is include_var_backtest
    assert provider.get_adjusted_prices.call_count == (
        int(include_market_data) + int(include_var_backtest)
    )
    assert not any(request.url.path.startswith("/ai/") for request in requests)
    assert any(message.startswith("PASS") for message in messages)
    if include_var_backtest:
        assert paths.index(("OPTIONS", VAR_PATH)) < paths.index(("POST", VAR_PATH))
        post = next(
            request
            for request in requests
            if request.method == "POST" and request.url.path == VAR_PATH
        )
        body = json.loads(post.content)
        assert [
            {"ticker": position["ticker"], "weight": position["weight"]}
            for position in body["positions"]
        ] == POSITIONS
        assert body["lookback_years"] == 3
        assert body["window_days"] == 252
        assert body["confidence_level"] == 0.95
        assert post.headers["origin"] == ORIGIN
        assert post.headers["x-risklens-client"] == "deployment-check"


@pytest.mark.parametrize("case", ["negative_var", "equal_loss", "all_breaches"])
def test_valid_signed_thresholds_and_statistical_rejection_are_not_probe_failures(
    var_probe_api,
    case,
):
    api, provider = var_probe_api
    original = provider.get_adjusted_prices.return_value.prices
    if case == "negative_var":
        values = 100 * np.cumprod(np.full(len(original), 1.001))
    elif case == "equal_loss":
        values = np.full(len(original), 100.0)
    else:
        returns = np.zeros(len(original))
        returns[253:] = -0.001 * np.arange(1, len(original) - 252)
        values = 100 * np.cumprod(1 + returns)
    provider.get_adjusted_prices.return_value = PriceHistory(
        prices=pd.DataFrame(
            {ticker: values for ticker in original.columns}, index=original.index
        ),
        source="Synthetic Test Data",
        warnings=[],
        provenance=provider.get_adjusted_prices.return_value.provenance,
    )
    inspected = []

    def handler(request):
        response = _proxy_response(api, request)
        if request.method == "POST" and request.url.path == VAR_PATH:
            inspected.append(response.json())
        return response

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    ) as client:
        check_deployment(client, ORIGIN, include_var_backtest=True)
    data = inspected[0]
    if case == "negative_var":
        assert all(point["var_loss"] < 0 for point in data["series"])
    elif case == "equal_loss":
        assert data["breach_count"] == 0
        assert all(
            point["var_loss"] == point["realized_loss"] for point in data["series"]
        )
        assert data["kupiec_test"]["reject_null"] is True
    else:
        assert data["breach_count"] == data["test_observations"]
        assert data["kupiec_test"]["reject_null"] is True
    assert data["kupiec_test"]["warning_codes"]


@pytest.mark.parametrize(
    "failure",
    [
        "legacy_missing_kupiec",
        "not_found",
        "html",
        "redirect",
        "provider_outage",
        "connection",
        "invalid_json_field",
        "post_cors",
        "options_cors",
        "options_method",
        "options_headers",
        "options_status",
    ],
)
def test_var_specific_http_schema_and_cors_failures_are_redacted(
    var_probe_api, failure
):
    api, _ = var_probe_api

    def handler(request):
        if request.url.path != VAR_PATH:
            return _proxy_response(api, request)
        if request.method == "POST":
            if failure == "connection":
                raise httpx.ConnectError(PRIVATE_DIAGNOSTIC, request=request)
            if failure in {"not_found", "provider_outage", "redirect"}:
                status = {"not_found": 404, "provider_outage": 503, "redirect": 307}[
                    failure
                ]
                return httpx.Response(status, text=PRIVATE_DIAGNOSTIC)
            if failure == "html":
                return httpx.Response(
                    200,
                    text=f"<html>{PRIVATE_DIAGNOSTIC}</html>",
                    headers={"access-control-allow-origin": ORIGIN},
                )
        response = _proxy_response(api, request)
        if request.method == "OPTIONS":
            if failure == "options_cors":
                del response.headers["access-control-allow-origin"]
            elif failure == "options_method":
                response.headers["access-control-allow-methods"] = "GET"
            elif failure == "options_headers":
                response.headers["access-control-allow-headers"] = "content-type"
            elif failure == "options_status":
                return httpx.Response(403, text=PRIVATE_DIAGNOSTIC)
        elif request.method == "POST":
            if failure == "post_cors":
                del response.headers["access-control-allow-origin"]
            elif failure in {"legacy_missing_kupiec", "invalid_json_field"}:
                data = response.json()
                if failure == "legacy_missing_kupiec":
                    data.pop("kupiec_test")
                else:
                    data["kupiec_test"]["statistic"] = PRIVATE_DIAGNOSTIC
                return httpx.Response(200, headers=response.headers, json=data)
        return response

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    ) as client:
        with pytest.raises(CheckFailed) as error:
            check_deployment(client, ORIGIN, include_var_backtest=True)
    assert PRIVATE_DIAGNOSTIC not in str(error.value)


@pytest.mark.parametrize(
    "failure",
    [
        "test_count",
        "breach_count",
        "breach_rate",
        "expected_count",
        "expected_rate",
        "sample_count",
        "window_days",
        "lookback_years",
        "test_start",
        "test_end",
        "sample_start",
        "sample_end",
        "duplicate_dates",
        "unsorted_dates",
        "invalid_date",
        "future_training_end",
        "reversed_training_dates",
        "training_before_sample",
        "later_training_before_sample",
        "training_start_moves_backwards",
        "loss_sign",
        "breach_flag",
        "nan_threshold",
        "infinite_return",
        "infinite_rate",
        "fractional_count",
        "string_count",
        "string_confidence",
        "string_breach_flag",
        "malformed_provenance_timestamp",
        "string_cache_hit",
        "kupiec_count",
        "kupiec_breaches",
        "kupiec_null_probability",
        "kupiec_observed_probability",
        "kupiec_decision",
        "kupiec_rounded_decision",
        "kupiec_nan_statistic",
        "kupiec_bad_probability",
        "kupiec_significance",
    ],
)
def test_inconsistent_var_series_and_kupiec_contract_fail_probe(var_probe_api, failure):
    api, _ = var_probe_api

    def handler(request):
        response = _proxy_response(api, request)
        if request.method != "POST" or request.url.path != VAR_PATH:
            return response
        data = response.json()
        first = data["series"][0]
        kupiec = data["kupiec_test"]
        if failure == "test_count":
            data["test_observations"] += 1
        elif failure == "breach_count":
            data["breach_count"] += 1
        elif failure == "breach_rate":
            data["breach_rate"] += 0.1
        elif failure == "expected_count":
            data["expected_breach_count"] += 1
        elif failure == "expected_rate":
            data["expected_breach_rate"] = 0.01
        elif failure == "sample_count":
            data["data_quality"]["observations"] += 1
        elif failure == "window_days":
            data["window_days"] += 1
        elif failure == "lookback_years":
            data["data_quality"]["requested_lookback_years"] = 5
        elif failure == "test_start":
            data["test_start"] = data["series"][1]["date"]
        elif failure == "test_end":
            data["test_end"] = data["series"][-2]["date"]
        elif failure == "sample_start":
            data["data_quality"]["start_date"] = first["date"]
        elif failure == "sample_end":
            data["data_quality"]["end_date"] = data["series"][-2]["date"]
        elif failure == "duplicate_dates":
            data["series"][1]["date"] = first["date"]
        elif failure == "unsorted_dates":
            data["series"][1], data["series"][2] = data["series"][2], data["series"][1]
        elif failure == "invalid_date":
            first["training_start"] = "not-a-date"
        elif failure == "future_training_end":
            first["training_end"] = first["date"]
        elif failure == "reversed_training_dates":
            first["training_start"] = first["date"]
        elif failure == "training_before_sample":
            first["training_start"] = "1999-01-01"
        elif failure == "later_training_before_sample":
            data["series"][1]["training_start"] = "1999-01-01"
        elif failure == "training_start_moves_backwards":
            data["series"][1]["training_start"] = first["training_start"]
        elif failure == "loss_sign":
            first["realized_loss"] = first["realized_return"]
        elif failure == "breach_flag":
            first["breach"] = not first["breach"]
        elif failure == "nan_threshold":
            first["var_loss"] = float("nan")
        elif failure == "infinite_return":
            first["realized_return"] = float("inf")
        elif failure == "infinite_rate":
            data["breach_rate"] = float("inf")
        elif failure == "fractional_count":
            data["breach_count"] = 0.5
        elif failure == "string_count":
            data["test_observations"] = str(data["test_observations"])
        elif failure == "string_confidence":
            data["confidence_level"] = str(data["confidence_level"])
        elif failure == "string_breach_flag":
            first["breach"] = "true" if first["breach"] else "false"
        elif failure == "malformed_provenance_timestamp":
            data["data_quality"]["provenance"]["fetched_at"] = "not-a-timestamp"
        elif failure == "string_cache_hit":
            data["data_quality"]["provenance"]["cache_hit"] = "false"
        elif failure == "kupiec_count":
            kupiec["observations"] += 1
        elif failure == "kupiec_breaches":
            kupiec["breaches"] += 1
        elif failure == "kupiec_null_probability":
            kupiec["null_breach_probability"] = 0.01
        elif failure == "kupiec_observed_probability":
            kupiec["observed_breach_probability"] = 0.9
        elif failure == "kupiec_decision":
            kupiec["reject_null"] = not kupiec["reject_null"]
        elif failure == "kupiec_rounded_decision":
            kupiec["p_value"] = np.nextafter(0.05, 0.0)
            kupiec["reject_null"] = False
        elif failure == "kupiec_nan_statistic":
            kupiec["statistic"] = float("nan")
        elif failure == "kupiec_bad_probability":
            kupiec["p_value"] = 1.1
        elif failure == "kupiec_significance":
            kupiec["significance_level"] = 0.1
        # JSON NaN/Infinity are intentionally emitted to test finite-value guards.
        return httpx.Response(
            200, headers=response.headers, content=json.dumps(data, allow_nan=True)
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    ) as client:
        with pytest.raises(CheckFailed):
            check_deployment(client, ORIGIN, include_var_backtest=True)


def test_cli_accepts_var_flag_and_succeeds_without_analysis(
    var_probe_api, monkeypatch, capsys
):
    api, provider = var_probe_api
    paths = []
    api.event_hooks["request"] = [lambda request: paths.append(request.url.path)]
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: api)
    assert main(["--include-var-backtest"]) == 0
    assert VAR_PATH in paths
    assert "/portfolio/analyze" not in paths
    provider.get_adjusted_prices.assert_called_once()
    assert "PASS" in capsys.readouterr().out


def test_cli_var_failure_returns_nonzero_without_sensitive_response(
    var_probe_api,
    monkeypatch,
    capsys,
):
    api, _ = var_probe_api

    def handler(request):
        if request.method == "POST" and request.url.path == VAR_PATH:
            return httpx.Response(503, text=PRIVATE_DIAGNOSTIC)
        return _proxy_response(api, request)

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    )
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    assert main(["--include-var-backtest"]) == 1
    output = capsys.readouterr().out
    assert "FAIL" in output
    assert "503" in output
    assert PRIVATE_DIAGNOSTIC not in output
