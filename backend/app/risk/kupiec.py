"""Kupiec's likelihood-ratio test of unconditional VaR breach frequency."""

from __future__ import annotations

import math
from numbers import Integral, Real

from scipy.stats import chi2

from app.models.var_backtest import KupiecTestResult, KupiecWarningCode


def kupiec_unconditional_coverage(
    *, observations: int, breaches: int, null_breach_probability: float
) -> KupiecTestResult:
    """Compare nominal and observed breach probabilities, using counts only.

    LR_uc = 2 * [x log((x / N) / p) + (N - x) log((1 - x / N) / (1 - p))].
    Zero-count terms are zero by continuity (0 log 0 = 0). Log differences avoid
    overflow in probability ratios, and log1p preserves precision near p = 0.
    The chi-square reference distribution has one degree of freedom. Both too
    few and too many breaches can reject; the survival probability is not doubled.
    """

    if (
        isinstance(observations, bool)
        or not isinstance(observations, Integral)
        or observations <= 0
    ):
        raise ValueError("Observations must be a positive integer")
    if (
        isinstance(breaches, bool)
        or not isinstance(breaches, Integral)
        or not 0 <= breaches <= observations
    ):
        raise ValueError("Breaches must be an integer between zero and observations")
    if (
        isinstance(null_breach_probability, bool)
        or not isinstance(null_breach_probability, Real)
        or not 0.0 < null_breach_probability < 1.0
    ):
        raise ValueError("Null breach probability must be finite and strictly between zero and one")
    probability = float(null_breach_probability)
    if not math.isfinite(probability) or not 0.0 < probability < 1.0:
        raise ValueError("Null breach probability must be finite and strictly between zero and one")
    observations = int(observations)
    breaches = int(breaches)
    try:
        float(observations)
    except OverflowError as exc:
        raise ValueError("Observation count is too large for a finite test statistic") from exc

    observed_probability = breaches / observations
    nonbreaches = observations - breaches
    breach_term = (
        breaches * (math.log(observed_probability) - math.log(probability))
        if breaches
        else 0.0
    )
    nonbreach_term = (
        nonbreaches * (math.log(nonbreaches / observations) - math.log1p(-probability))
        if nonbreaches
        else 0.0
    )
    statistic = 2.0 * (breach_term + nonbreach_term)
    if not math.isfinite(statistic):
        raise ValueError("Observation count is too large for a finite test statistic")
    # LR is nonnegative analytically. Remove negative floating-point roundoff,
    # and preserve an exact zero when the observed and nominal rates match.
    statistic = 0.0 if observed_probability == probability else max(0.0, statistic)
    p_value = float(chi2.sf(statistic, df=1))
    warning_codes: list[KupiecWarningCode] = []
    if observations * probability < 5 or observations * (1.0 - probability) < 5:
        warning_codes.append("low_expected_counts")
    if breaches in (0, observations):
        warning_codes.append("boundary_breach_count")

    return KupiecTestResult(
        statistic=statistic,
        p_value=p_value,
        reject_null=p_value < 0.05,
        null_breach_probability=probability,
        observed_breach_probability=observed_probability,
        observations=observations,
        breaches=breaches,
        warning_codes=warning_codes,
    )
