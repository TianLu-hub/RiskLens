"""Asset-return correlation analysis."""

from __future__ import annotations

import pandas as pd


def correlation_matrix(asset_returns: pd.DataFrame) -> pd.DataFrame:
    """Calculate the Pearson correlation matrix."""

    return asset_returns.corr()


def strongest_pairs(
    correlation: pd.DataFrame, limit: int = 5
) -> list[dict[str, str | float]]:
    """Return the strongest distinct pairs, excluding self-correlation."""

    pairs: list[dict[str, str | float]] = []
    columns = list(correlation.columns)
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            value = correlation.loc[left, right]
            if pd.isna(value):
                continue
            pairs.append(
                {"asset_1": left, "asset_2": right, "correlation": float(value)}
            )
    return sorted(pairs, key=lambda pair: float(pair["correlation"]), reverse=True)[
        :limit
    ]
