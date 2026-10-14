"""Portfolio request validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.portfolio import AnalyzeRequest


def test_weights_sum_to_one() -> None:
    request = AnalyzeRequest(
        positions=[
            {"ticker": " aapl ", "weight": 0.6},
            {"ticker": "MSFT", "weight": 0.4},
        ]
    )
    assert request.positions[0].ticker == "AAPL"
    assert sum(position.weight for position in request.positions) == pytest.approx(1.0)


def test_invalid_weight_sum_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must sum to 1.0"):
        AnalyzeRequest(
            positions=[
                {"ticker": "AAPL", "weight": 0.7},
                {"ticker": "MSFT", "weight": 0.2},
            ]
        )


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            positions=[
                {"ticker": "AAPL", "weight": 1.1},
                {"ticker": "TLT", "weight": -0.1},
            ]
        )


def test_duplicate_ticker_is_rejected_after_normalization() -> None:
    with pytest.raises(ValidationError, match="only once"):
        AnalyzeRequest(
            positions=[
                {"ticker": "aapl", "weight": 0.5},
                {"ticker": "AAPL", "weight": 0.5},
            ]
        )
