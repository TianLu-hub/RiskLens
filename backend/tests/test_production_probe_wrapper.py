"""Exercise the actual workflow wrapper without network or paid model calls."""

import json
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "probe_production.sh"


@pytest.fixture
def run_wrapper(tmp_path):
    executable = tmp_path / "python"
    executable.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$@" > "$TEST_ARGUMENTS"\n'
        'if [[ "$TEST_EXIT" != "2" ]]; then\n'
        '  printf \'{"schema_version":1,"status":"%s"}\\n\' "$TEST_STATUS"\n'
        "else\n"
        '  printf "invalid CLI arguments\\n" >&2\n'
        "fi\n"
        'exit "$TEST_EXIT"\n'
    )
    executable.chmod(0o755)

    def run(code=0, **inputs):
        env = os.environ.copy()
        for key in ("EXPECTED_REVISION", "INCLUDE_MARKET_DATA", "INCLUDE_VAR_BACKTEST"):
            env.pop(key, None)
        env.update(
            PATH=str(tmp_path) + os.pathsep + env["PATH"],
            RUNNER_TEMP=str(tmp_path),
            GITHUB_OUTPUT=str(tmp_path / "outputs"),
            TEST_ARGUMENTS=str(tmp_path / "args"),
            TEST_EXIT=str(code),
            TEST_STATUS="passed" if code == 0 else "failed",
            **inputs,
        )
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            cwd=SCRIPT.parents[1],
            check=False,
        )
        return result, tmp_path, (tmp_path / "args").read_text().splitlines()

    return run


@pytest.mark.parametrize("exit_code", [0, 1, 2])
def test_wrapper_preserves_probe_exit_and_only_marks_nonempty_reports(
    run_wrapper, exit_code
):
    result, directory, args = run_wrapper(exit_code)
    assert result.returncode == exit_code
    assert args[:3] == ["-m", "scripts.check_deployment", "--json"]
    assert "--include-market-data" not in args
    assert "--include-var-backtest" not in args
    assert "--expected-revision" not in args
    assert args[args.index("--api-url") + 1] == (
        "https://balanced-intuition-production-6020.up.railway.app"
    )
    report = (directory / "risklens-probe.json").read_text()
    if exit_code == 2:
        assert report == ""
        assert not (directory / "outputs").exists()
        assert "invalid CLI arguments" in result.stderr
    else:
        assert json.loads(report)["status"] == (
            "passed" if exit_code == 0 else "failed"
        )
        assert report == result.stdout
        assert (directory / "outputs").read_text() == "report_available=true\n"


@pytest.mark.parametrize(
    "market,var", [("true", "false"), ("false", "true"), ("true", "true")]
)
def test_optional_probes_and_revision_are_forwarded(run_wrapper, market, var):
    sha = "abcdef01" * 5
    result, _, args = run_wrapper(
        EXPECTED_REVISION=sha, INCLUDE_MARKET_DATA=market, INCLUDE_VAR_BACKTEST=var
    )
    assert result.returncode == 0
    assert ("--include-market-data" in args) == (market == "true")
    assert ("--include-var-backtest" in args) == (var == "true")
    assert args[args.index("--expected-revision") + 1] == sha


def test_revision_is_passed_as_data_not_evaluated_as_shell(run_wrapper, tmp_path):
    injected = f"$(touch {tmp_path / 'should-not-exist'})"
    _, _, args = run_wrapper(EXPECTED_REVISION=injected)
    assert args[args.index("--expected-revision") + 1] == injected
    assert not (tmp_path / "should-not-exist").exists()
