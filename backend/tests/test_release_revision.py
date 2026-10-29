"""Release metadata is opt-in, validated, and distinct from liveness."""

import argparse

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts.check_deployment import (
    CheckFailed,
    check_deployment,
    commit_revision,
    main,
)

SHA = "abcdef01" * 5
ORIGIN = "http://localhost:3000"


@pytest.mark.parametrize(
    "value", [None, "", "main", "abc1234", "private-token", "f" * 41]
)
def test_health_does_not_expose_invalid_revision(monkeypatch, value):
    monkeypatch.delenv("RISKLENS_REVISION", raising=False)
    if value is not None:
        monkeypatch.setenv("RISKLENS_REVISION", value)
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["revision"] is None
    assert response.json()["status"] == "ok"
    assert "private-token" not in response.text


def test_health_normalizes_full_revision(monkeypatch):
    monkeypatch.setenv("RISKLENS_REVISION", " " + SHA.upper() + " ")
    assert TestClient(app).get("/health").json()["revision"] == SHA


@pytest.mark.parametrize(
    "value", ["", "main", "abc1234", "g" * 40, "f" * 41, SHA + "\n"]
)
def test_expected_revision_requires_full_sha(value):
    with pytest.raises(argparse.ArgumentTypeError):
        commit_revision(value)


def test_matching_revision_passes_without_changing_default_checks(monkeypatch):
    monkeypatch.setenv("RISKLENS_REVISION", SHA)
    client = TestClient(app)
    normal = check_deployment(client, ORIGIN)
    checked = check_deployment(client, ORIGIN, expected_revision=SHA.upper())
    revision_messages = [
        message for message in checked if message.startswith("PASS revision")
    ]
    assert len(revision_messages) == 1
    assert [
        message for message in checked if message not in revision_messages
    ] == normal


@pytest.mark.parametrize("reported", [None, "0" * 40, "private-upstream-diagnostic"])
def test_missing_or_wrong_revision_stops_before_other_requests(reported):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        payload = {"status": "ok", "service": "risklens-api", "version": "0.6.0"}
        if reported is not None:
            payload["revision"] = reported
        return httpx.Response(
            200, json=payload, headers={"access-control-allow-origin": ORIGIN}
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    ) as client:
        with pytest.raises(CheckFailed, match="[Rr]evision") as exc:
            check_deployment(
                client,
                ORIGIN,
                expected_revision=SHA,
                include_market_data=True,
                include_var_backtest=True,
            )
    assert paths == ["/health"]
    assert "private-upstream-diagnostic" not in str(exc.value)


def test_legacy_health_remains_compatible_without_revision_check(monkeypatch):
    monkeypatch.delenv("RISKLENS_REVISION", raising=False)
    api = TestClient(app)

    def handler(request):
        response = api.request(
            request.method,
            request.url.path,
            headers=request.headers,
            content=request.content,
        )
        if request.url.path == "/health":
            payload = response.json()
            payload.pop("revision")
            return httpx.Response(
                200, json=payload, headers={"access-control-allow-origin": ORIGIN}
            )
        return httpx.Response(
            response.status_code, content=response.content, headers=response.headers
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.example"
    ) as client:
        assert any(
            message.startswith("PASS stress")
            for message in check_deployment(client, ORIGIN)
        )


@pytest.mark.parametrize("matches", [False, True])
def test_cli_revision_option_controls_exit_status(monkeypatch, capsys, matches):
    monkeypatch.setenv("RISKLENS_REVISION", SHA if matches else "0" * 40)
    client = TestClient(app)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    assert main(["--expected-revision", SHA]) == (0 if matches else 1)
    assert (
        "PASS revision" if matches else "FAIL Release revision mismatch"
    ) in capsys.readouterr().out


def test_invalid_cli_revision_exits_before_connecting(monkeypatch):
    def no_connection(**kwargs):
        pytest.fail("Invalid commit must not trigger a request")

    monkeypatch.setattr(httpx, "Client", no_connection)
    with pytest.raises(SystemExit) as exc:
        main(["--expected-revision", "main"])
    assert exc.value.code == 2
