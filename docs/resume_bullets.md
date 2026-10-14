# RiskLens resume bullets

These versions intentionally describe a research-grade portfolio project without implying institutional production accuracy.

## Quant-focused

- Built a deterministic portfolio-risk engine in Python for annualized return and volatility, historical VaR/CVaR, drawdown, correlation, concentration, Euler volatility-risk decomposition, SPY market-factor regression, and hypothetical multi-factor stress testing across user-defined equity and ETF portfolios.
- Added long-only minimum-volatility, maximum-Sharpe, and risk-parity allocation comparisons with position caps, turnover reporting, and explicit in-sample limitations.
- Implemented a chronological walk-forward backtest that refits allocation weights on trailing windows and compares later, unseen returns with a fixed-weight baseline, including drift-aware rebalancing and configurable transaction-cost assumptions.
- Implemented numerical invariants and unit tests for covariance-based volatility, geometric annualization, tail-loss estimates, HHI/effective positions, risk contributions summing to 100%, regression alpha/beta recovery, duration-shock direction, and P&L attribution reconciliation.
- Designed a replaceable market-data layer around adjusted Yahoo Finance histories with date alignment, caching, missing-data handling, and explicit data-quality warnings.

## Data / ML-focused

- Developed an analytics pipeline that converts multi-asset price histories into aligned returns, portfolio time series, tail-risk estimates, correlation structure, SPY factor exposures, explainable rule-based risk flags, and structured hypothetical stress outputs.
- Implemented a zero-cost deterministic interpretation layer for bounded English and Chinese shock language, with an optional structured LLM adapter; both paths delegate every calculation to Python and explain only backend-supplied results.
- Created a typed FastAPI contract and deterministic synthetic test fixtures for reproducible validation without depending on live market-data availability.

## Software / AI-focused

- Built a modular full-stack risk terminal using TypeScript, React/Next.js-compatible Vinext, Tailwind, Recharts, FastAPI, Pydantic, pandas, and NumPy, with Dockerized local deployment.
- Designed reusable dashboard components for portfolio editing, risk summaries, correlation heatmaps, drawdowns, concentration, volatility contribution, rolling factor exposure, stress attribution, and constrained allocation comparison with resilient loading and error states.
- Built a Risk Officer with a deterministic default, optional Pydantic Structured Outputs adapter, natural-language scenario parsing, Python stress-engine execution, and backend-injected evidence values; narrative prose is schema-constrained to contain no numerical claims.
