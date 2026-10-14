"""Long-only historical optimization using bounded SLSQP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.risk.metrics import TRADING_DAYS

Objective = Literal["minimum_volatility", "maximum_sharpe", "risk_parity"]


class OptimizationUnavailableError(ValueError):
    """Raised when a constrained solution cannot be estimated reliably."""


@dataclass(frozen=True)
class OptimizedWeights:
    weights: np.ndarray
    covariance_regularized: bool


def optimize_weights(
    asset_returns: pd.DataFrame,
    current_weights: np.ndarray,
    objective: Objective,
    risk_free_rate: float,
    max_position_weight: float | None,
) -> OptimizedWeights:
    """Find a feasible allocation on the simplex, using multiple fixed starts."""

    observations, count = asset_returns.shape
    if observations < 2 or count == 0 or len(current_weights) != count:
        raise OptimizationUnavailableError("Insufficient aligned asset returns.")
    cap = max_position_weight if max_position_weight is not None else 1.0
    if count * cap < 1.0 - 1e-10:
        raise OptimizationUnavailableError("The position cap is infeasible.")
    if count == 1:
        return OptimizedWeights(weights=np.array([1.0]), covariance_regularized=False)

    returns = asset_returns.to_numpy(dtype=float)
    if not np.isfinite(returns).all():
        raise OptimizationUnavailableError("Asset returns contain non-finite values.")
    covariance = np.cov(returns, rowvar=False, ddof=1) * TRADING_DAYS
    covariance = np.atleast_2d(covariance)
    covariance = (covariance + covariance.T) / 2
    eigenvalues = np.linalg.eigvalsh(covariance)
    if eigenvalues[-1] <= 1e-14:
        raise OptimizationUnavailableError(
            "All asset returns have zero sample volatility."
        )
    ridge = max(float(eigenvalues[-1]) * 1e-8, 1e-10)
    regularized = bool(eigenvalues[0] < ridge)
    if regularized:
        covariance += np.eye(count) * (ridge - float(eigenvalues[0]))

    def variance(weights: np.ndarray) -> float:
        return float(weights @ covariance @ weights)

    def score(weights: np.ndarray) -> float:
        var = variance(weights)
        if objective == "minimum_volatility":
            return var
        if var <= 1e-14:
            return 1e9
        if objective == "risk_parity":
            contributions = weights * (covariance @ weights) / var
            return float(np.square(contributions - 1.0 / count).sum())
        if objective == "maximum_sharpe":
            portfolio_daily = returns @ weights
            if np.any(portfolio_daily <= -1):
                return 1e9
            annual_return = float(
                np.expm1(np.log1p(portfolio_daily).mean() * TRADING_DAYS)
            )
            return -(annual_return - risk_free_rate) / np.sqrt(var)
        raise ValueError(f"Unsupported objective: {objective}")

    equal = np.full(count, 1.0 / count)
    starts = [equal]
    if np.max(current_weights) <= cap + 1e-10:
        starts.append(np.asarray(current_weights, dtype=float))
    # A concentrated feasible start helps the non-convex Sharpe objective.
    ordered = np.argsort(returns.mean(axis=0))[::-1]
    concentrated = np.zeros(count)
    remaining = 1.0
    for index in ordered:
        amount = min(cap, remaining)
        concentrated[index] = amount
        remaining -= amount
        if remaining <= 1e-12:
            break
    starts.append(concentrated)

    bounds = [(0.0, cap)] * count
    constraint = {"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0}
    candidates: list[np.ndarray] = []
    for start in starts:
        result = minimize(
            score,
            start,
            method="SLSQP",
            bounds=bounds,
            constraints=[constraint],
            options={"ftol": 1e-11, "maxiter": 800},
        )
        if result.success and _feasible(result.x, cap):
            candidates.append(np.asarray(result.x, dtype=float))
    if not candidates:
        raise OptimizationUnavailableError(
            "The optimizer could not find a feasible solution for these inputs."
        )
    best = min(candidates, key=score)
    return OptimizedWeights(weights=best, covariance_regularized=regularized)


def _feasible(weights: np.ndarray, cap: float) -> bool:
    return bool(
        np.isfinite(weights).all()
        and abs(float(weights.sum()) - 1.0) <= 1e-6
        and np.min(weights) >= -1e-7
        and np.max(weights) <= cap + 1e-7
    )
