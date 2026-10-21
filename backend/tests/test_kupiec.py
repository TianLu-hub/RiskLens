"""Independent likelihood values, numerical boundaries, and Kupiec test contracts."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.risk.kupiec import kupiec_unconditional_coverage


@pytest.mark.parametrize(
    ("breaches", "statistic", "p_value", "reject"),
    [
        (5, 6.07148034557369, 0.0137381772609852, True),
        (13, 0.0207919130316299, 0.885347269442574, False),
        (25, 10.3271094563732, 0.00131090347244753, True),
    ],
)
def test_known_interior_likelihood_ratios(
    breaches: int, statistic: float, p_value: float, reject: bool,
) -> None:
    result = kupiec_unconditional_coverage(
        observations=250, breaches=breaches, null_breach_probability=0.05
    )
    assert result.statistic == pytest.approx(statistic, rel=1e-11)
    assert result.p_value == pytest.approx(p_value, rel=1e-11)
    # For df=1, the chi-square survival probability has this independent form.
    assert result.p_value == pytest.approx(math.erfc(math.sqrt(statistic / 2)), rel=1e-11)
    assert result.reject_null is reject
    assert result.warning_codes == []


@pytest.mark.parametrize("breaches", [0, 250])
def test_zero_and_all_breaches_have_finite_boundary_likelihoods(breaches: int) -> None:
    result = kupiec_unconditional_coverage(
        observations=250, breaches=breaches, null_breach_probability=0.01
    )
    probability_of_outcome = 0.99 if breaches == 0 else 0.01
    expected = -2 * 250 * math.log(probability_of_outcome)
    assert result.statistic == pytest.approx(expected)
    assert result.p_value == pytest.approx(math.erfc(math.sqrt(expected / 2)))
    assert math.isfinite(result.statistic)
    assert result.observed_breach_probability == breaches / 250
    assert result.warning_codes == ["low_expected_counts", "boundary_breach_count"]


def test_exact_nominal_frequency_returns_zero_statistic_and_unit_p_value() -> None:
    result = kupiec_unconditional_coverage(
        observations=100, breaches=5, null_breach_probability=0.05
    )
    assert result.statistic == 0.0
    assert result.p_value == 1.0
    assert result.reject_null is False
    assert result.warning_codes == []
    assert result.null_breach_probability == result.observed_breach_probability == 0.05


@pytest.mark.parametrize(
    "probability", [np.nextafter(0.0, 1.0), 1e-300, 1.0 - 1e-15, np.nextafter(1.0, 0.0)]
)
@pytest.mark.parametrize("breaches", [0, 5, 100])
def test_extreme_valid_probabilities_never_produce_nan_or_infinity(
    probability: float, breaches: int,
) -> None:
    result = kupiec_unconditional_coverage(
        observations=100, breaches=breaches, null_breach_probability=probability
    )
    assert math.isfinite(result.statistic)
    assert result.statistic >= 0
    assert math.isfinite(result.p_value)
    assert 0 <= result.p_value <= 1
    assert result.reject_null is (result.p_value < 0.05)
    assert "low_expected_counts" in result.warning_codes


def test_boundary_warning_is_independent_of_expected_count_warning() -> None:
    result = kupiec_unconditional_coverage(
        observations=100, breaches=0, null_breach_probability=0.05
    )
    assert result.warning_codes == ["boundary_breach_count"]


@pytest.mark.parametrize("probability", [0.01, 0.99])
def test_either_low_expected_category_triggers_warning(probability: float) -> None:
    result = kupiec_unconditional_coverage(
        observations=100, breaches=50, null_breach_probability=probability
    )
    assert result.warning_codes == ["low_expected_counts"]


@pytest.mark.parametrize(
    ("p_value", "reject"),
    [(0.05, False), (np.nextafter(0.05, 0.0), True), (np.nextafter(0.05, 1.0), False)],
)
def test_rejection_uses_unrounded_p_value_strictly_below_fixed_significance(
    p_value: float, reject: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.risk.kupiec.chi2.sf", lambda statistic, df: p_value)
    result = kupiec_unconditional_coverage(
        observations=100, breaches=10, null_breach_probability=0.05
    )
    assert result.significance_level == 0.05
    assert result.reject_null is reject


def test_test_is_invariant_to_breach_order() -> None:
    clustered = [True] * 10 + [False] * 90
    dispersed = [True] + [False] * 9
    dispersed *= 10
    first = kupiec_unconditional_coverage(
        observations=len(clustered),
        breaches=sum(clustered),
        null_breach_probability=0.05,
    )
    second = kupiec_unconditional_coverage(
        observations=len(dispersed),
        breaches=sum(dispersed),
        null_breach_probability=0.05,
    )
    assert first == second


def test_numpy_scalar_counts_are_supported_without_integer_overflow() -> None:
    result = kupiec_unconditional_coverage(
        observations=np.int64(100),
        breaches=np.int64(5),
        null_breach_probability=np.float64(0.05),
    )
    assert result.observations == 100
    assert result.breaches == 5
    assert result.statistic == 0.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"observations": 0},
        {"observations": -1},
        {"observations": 100.0},
        {"observations": True},
        {"observations": "100"},
        {"observations": np.nan},
        {"observations": np.inf},
        {"breaches": -1},
        {"breaches": 101},
        {"breaches": 5.0},
        {"breaches": False},
        {"breaches": "5"},
        {"breaches": np.nan},
        {"breaches": np.inf},
        {"null_breach_probability": 0.0},
        {"null_breach_probability": 1.0},
        {"null_breach_probability": -0.1},
        {"null_breach_probability": 1.1},
        {"null_breach_probability": np.nan},
        {"null_breach_probability": np.inf},
        {"null_breach_probability": -np.inf},
        {"null_breach_probability": True},
        {"null_breach_probability": "0.05"},
        {"null_breach_probability": complex(0.05, 0)},
        {"null_breach_probability": None},
    ],
)
def test_invalid_counts_types_and_probabilities_are_rejected(
    overrides: dict[str, object],
) -> None:
    parameters = {"observations": 100, "breaches": 5, "null_breach_probability": 0.05}
    with pytest.raises(ValueError):
        kupiec_unconditional_coverage(**(parameters | overrides))


@pytest.mark.parametrize("observations", [10**400, 10**308])
def test_counts_too_large_for_finite_statistic_are_rejected(observations: int) -> None:
    with pytest.raises(ValueError, match="too large"):
        kupiec_unconditional_coverage(
            observations=observations,
            breaches=observations,
            null_breach_probability=0.01,
        )
