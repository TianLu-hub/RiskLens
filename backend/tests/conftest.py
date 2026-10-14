"""Shared deterministic fixtures for backend tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def asset_returns() -> pd.DataFrame:
    index = pd.bdate_range("2024-01-02", periods=8)
    return pd.DataFrame(
        {
            "AAPL": [0.010, -0.020, 0.015, 0.004, -0.006, 0.011, 0.003, -0.008],
            "MSFT": [0.008, -0.010, 0.012, 0.003, -0.004, 0.009, 0.005, -0.005],
            "TLT": [-0.002, 0.006, -0.003, 0.001, 0.005, -0.002, 0.001, 0.004],
        },
        index=index,
    )


@pytest.fixture
def weights() -> np.ndarray:
    return np.asarray([0.4, 0.35, 0.25])
