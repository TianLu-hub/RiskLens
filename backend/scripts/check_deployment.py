"""Check a running API and browser CORS configuration without calling an LLM."""

from __future__ import annotations

import argparse
import math
from collections.abc import Sequence

import httpx
from pydantic import ValidationError

from app.models.responses import HealthResponse, PortfolioAnalysisResponse
from app.models.stress import StressTestResponse
from app.models.var_backtest import VarBacktestRequest, VarBacktestResponse
from scripts.var_probe import validate_var_response


class CheckFailed(Exception):
    """An actionable deployment check failed."""


def origin_url(value: str) -> str:
    """Accept only an HTTP(S) origin, never credentials, paths, or query secrets."""

    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as exc:
        raise argparse.ArgumentTypeError("Expected an HTTP(S) origin") from exc
    if (
        url.scheme not in {"http", "https"}
        or not url.host
        or url.userinfo
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
    ):
        raise argparse.ArgumentTypeError(
            "Use an HTTP(S) origin without credentials, path, query, or fragment"
        )
    return str(url).rstrip("/")


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Timeout must be a positive number") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("Timeout must be a positive finite number")
    return timeout


def require_cors(response: httpx.Response, origin: str) -> None:
    """Match the dashboard's non-credentialed browser request policy."""

    if response.headers.get("access-control-allow-origin") not in {origin, "*"}:
        raise CheckFailed("Browser access blocked: check backend CORS_ORIGINS")


def check_preflight(client: httpx.Client, origin: str, path: str) -> None:
    """Check the exact route; a proxy can apply different CORS rules per path."""

    response = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-risklens-client",
        },
    )
    response.raise_for_status()
    require_cors(response, origin)
    methods = {
        item.strip().upper()
        for item in response.headers.get("access-control-allow-methods", "").split(",")
    }
    headers = {
        item.strip().lower()
        for item in response.headers.get("access-control-allow-headers", "").split(",")
    }
    if "POST" not in methods or not (
        "*" in headers or {"content-type", "x-risklens-client"} <= headers
    ):
        raise CheckFailed("Preflight does not allow the dashboard POST headers/method")


def default_portfolio_input() -> dict:
    """Use the same public example for both optional history probes."""

    return {
        "positions": [
            {"ticker": ticker, "weight": weight}
            for ticker, weight in [
                ("AAPL", 0.20),
                ("MSFT", 0.20),
                ("NVDA", 0.15),
                ("SPY", 0.25),
                ("TLT", 0.20),
            ]
        ],
        "lookback_years": 3,
        "risk_free_rate": 0.04,
    }


def check_deployment(
    client: httpx.Client,
    origin: str,
    *,
    include_market_data: bool = False,
    include_var_backtest: bool = False,
) -> list[str]:
    """Probe health, CORS, stress, and independently selected historical checks."""

    passed: list[str] = []
    stage = "health"
    try:
        response = client.get("/health", headers={"Origin": origin})
        response.raise_for_status()
        health = HealthResponse.model_validate(response.json())
        if health.status != "ok" or health.service != "risklens-api":
            raise CheckFailed("Unexpected service: verify the backend API URL")
        require_cors(response, origin)
        passed.append("PASS health: RiskLens API is reachable")

        stage = "CORS preflight"
        check_preflight(client, origin, "/portfolio/stress-test")
        passed.append("PASS CORS: browser origin and POST headers are allowed")

        stage = "stress endpoint"
        response = client.post(
            "/portfolio/stress-test",
            headers={"Origin": origin, "X-RiskLens-Client": "deployment-check"},
            json={
                "positions": [{"ticker": "TLT", "weight": 1.0}],
                "rates_shock_bps": 100,
                "portfolio_value": 100000,
                "scenario_name": "Deployment check (hypothetical)",
            },
        )
        response.raise_for_status()
        require_cors(response, origin)
        result = StressTestResponse.model_validate(response.json())
        if result.historical_data_used or not result.asset_contributions:
            raise CheckFailed("Stress response is missing its hypothetical result")
        passed.append("PASS stress: typed hypothetical result returned")

        if include_market_data:
            stage = "market analysis"
            response = client.post(
                "/portfolio/analyze",
                headers={"Origin": origin, "X-RiskLens-Client": "deployment-check"},
                json=default_portfolio_input(),
            )
            response.raise_for_status()
            require_cors(response, origin)
            analysis = PortfolioAnalysisResponse.model_validate(response.json())
            if analysis.data_quality.observations <= 0 or not analysis.performance:
                raise CheckFailed("Analysis contains no historical observations")
            passed.append(
                f"PASS analysis: {analysis.data_quality.observations} return observations"
            )
        else:
            passed.append("SKIP market analysis: use --include-market-data to check it")

        if include_var_backtest:
            stage = "VaR CORS preflight"
            check_preflight(client, origin, "/portfolio/var-backtest")
            stage = "VaR backtest"
            request = VarBacktestRequest(
                **default_portfolio_input(), window_days=252, confidence_level=0.95
            )
            response = client.post(
                "/portfolio/var-backtest",
                headers={"Origin": origin, "X-RiskLens-Client": "deployment-check"},
                json=request.model_dump(),
            )
            response.raise_for_status()
            require_cors(response, origin)
            # JSON timestamps are strings; validate in JSON mode so provenance
            # datetimes remain valid without coercing numeric or boolean fields.
            result = VarBacktestResponse.model_validate_json(
                response.content, strict=True
            )
            try:
                validate_var_response(result, request)
            except ValueError as exc:
                raise CheckFailed(
                    "VaR backtest: response is internally inconsistent"
                ) from exc
            passed.append(
                f"PASS VaR/Kupiec: {result.test_observations} out-of-sample days, "
                f"{result.breach_count} breaches; response contract is consistent"
            )
    except httpx.HTTPStatusError as exc:
        # Do not echo response bodies: proxies may return sensitive diagnostic HTML.
        raise CheckFailed(f"{stage}: HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise CheckFailed(
            f"{stage}: connection/TLS/timeout failure; check API URL and service status"
        ) from exc
    except (ValidationError, ValueError) as exc:
        raise CheckFailed(f"{stage}: response is not valid RiskLens JSON") from exc
    return passed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", type=origin_url, default="http://127.0.0.1:8000")
    parser.add_argument("--origin", type=origin_url, default="http://localhost:3000")
    parser.add_argument("--timeout", type=positive_timeout, default=30.0)
    parser.add_argument(
        "--include-market-data",
        action="store_true",
        help="Also analyze the default portfolio (may fetch Yahoo history or use cache)",
    )
    parser.add_argument(
        "--include-var-backtest",
        action="store_true",
        help="Also verify rolling VaR/Kupiec and its CORS route (may fetch Yahoo history)",
    )
    args = parser.parse_args(argv)
    try:
        with httpx.Client(
            base_url=args.api_url, timeout=args.timeout, follow_redirects=False
        ) as client:
            messages = check_deployment(
                client,
                args.origin,
                include_market_data=args.include_market_data,
                include_var_backtest=args.include_var_backtest,
            )
    except CheckFailed as exc:
        print(f"FAIL {exc}")
        return 1
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
