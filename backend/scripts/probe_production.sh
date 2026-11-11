#!/usr/bin/env bash
# GitHub Actions wrapper: preserve the probe exit code and its sanitized report.
set -euo pipefail

: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
report="$RUNNER_TEMP/risklens-probe.json"
trap 'if [[ -s "$report" ]]; then printf "report_available=true\n" >> "$GITHUB_OUTPUT"; fi' EXIT

args=(
  --json
  --api-url https://balanced-intuition-production-6020.up.railway.app
  --origin https://risklens-ai-portfolio-risk-terminal.tianlu923.chatgpt.site
  --timeout 60
)
if [[ -n "${EXPECTED_REVISION:-}" ]]; then
  args+=(--expected-revision "$EXPECTED_REVISION")
fi
if [[ "${INCLUDE_MARKET_DATA:-false}" == "true" ]]; then
  args+=(--include-market-data)
fi
if [[ "${INCLUDE_VAR_BACKTEST:-false}" == "true" ]]; then
  args+=(--include-var-backtest)
fi
python -m scripts.check_deployment "${args[@]}" | tee "$report"
