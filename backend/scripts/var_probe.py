"""Response consistency checks, not an independent VaR or likelihood estimator."""

from __future__ import annotations

import math
from datetime import date

from app.models.var_backtest import VarBacktestRequest, VarBacktestResponse
from app.risk.var_backtest import MIN_TEST_OBSERVATIONS


def _close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and math.isclose(
        actual, expected, rel_tol=1e-9, abs_tol=1e-12
    )


def _date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if value != parsed.isoformat():
        raise ValueError("Dates must use the API's ISO date format")
    return parsed


def validate_var_response(
    result: VarBacktestResponse, request: VarBacktestRequest
) -> None:
    """Reject mismatched summaries or chronology without recalculating forecasts.

    Signed (including negative) VaR is valid. A statistical rejection is a valid
    outcome, not a deployment failure. Errors are redacted by the CLI caller.
    """

    observations = len(result.series)
    if (
        result.window_days != request.window_days
        or not _close(result.confidence_level, request.confidence_level)
        or observations < MIN_TEST_OBSERVATIONS
        or result.test_observations != observations
        or result.data_quality.observations != observations + request.window_days
        or result.data_quality.requested_lookback_years != request.lookback_years
    ):
        raise ValueError("The requested model or sample size does not match")

    first, last = result.series[0], result.series[-1]
    if (
        _date(result.test_start) != _date(first.date)
        or _date(result.test_end) != _date(last.date)
        or _date(result.data_quality.start_date) != _date(first.training_start)
        or _date(result.data_quality.end_date) != _date(last.date)
    ):
        raise ValueError("Sample date boundaries do not match the forecast record")

    previous_day = None
    previous_training_start = None
    for point in result.series:
        test_day = _date(point.date)
        training_start = _date(point.training_start)
        training_end = _date(point.training_end)
        if (
            not training_start <= training_end < test_day
            or (previous_day is not None and training_end != previous_day)
            or (
                previous_training_start is not None
                and training_start <= previous_training_start
            )
        ):
            raise ValueError("Forecast dates or training chronology are inconsistent")
        if (
            not math.isfinite(point.var_loss)
            or not _close(point.realized_loss, -point.realized_return)
            or point.breach != (point.realized_loss > point.var_loss)
        ):
            raise ValueError("Daily loss or breach flags are inconsistent")
        previous_day = test_day
        previous_training_start = training_start

    breaches = sum(point.breach for point in result.series)
    nominal_rate = 1.0 - request.confidence_level
    observed_rate = breaches / observations
    kupiec = result.kupiec_test
    if (
        result.breach_count != breaches
        or not _close(result.breach_rate, observed_rate)
        or not _close(result.expected_breach_rate, nominal_rate)
        or not _close(result.expected_breach_count, observations * nominal_rate)
        or kupiec.observations != observations
        or kupiec.breaches != breaches
        or not _close(kupiec.null_breach_probability, nominal_rate)
        or not _close(kupiec.observed_breach_probability, observed_rate)
        or kupiec.reject_null != (kupiec.p_value < kupiec.significance_level)
    ):
        raise ValueError("Breach summaries or Kupiec evidence are inconsistent")
