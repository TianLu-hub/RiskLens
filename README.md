# RiskLens

A web dashboard for checking the risk of a stock and ETF portfolio. Enter tickers and weights, then look at the portfolio's historical behavior. RiskLens does not trade or manage an account.

[Live demo](https://risklens-ai-portfolio-risk-terminal.tianlu923.chatgpt.site/) · [中文说明](README.zh-CN.md)

## What it does

- Shows return, volatility, Sharpe ratio, drawdown, historical VaR/CVaR, correlations, and each holding's share of risk.
- Runs hypothetical market, tech, interest-rate, and single-ticker shocks. Results include estimated P&L and the assumptions used.
- Estimates market exposure with a regression against SPY.
- Compares the current weights with minimum-volatility, maximum-Sharpe, or risk-parity weights.
- Runs a walk-forward backtest: fit weights on earlier data, then evaluate them on later dates.
- Explains the calculated results in plain language through the Risk Officer.

The default portfolio is AAPL 20%, MSFT 20%, NVDA 15%, SPY 25%, and TLT 20%. You can replace it with your own holdings. Weights must be nonnegative and add up to 100%; short positions are not supported.

## How it works

~~~text
Browser (React / TypeScript)
        |
        v
FastAPI (Python) <--- Yahoo Finance historical daily prices
        |
        +-- Risk metrics, factor regression, and stress tests
        +-- Optimization and walk-forward backtest
        +-- Risk Officer explains the computed results
~~~

Financial numbers are calculated by Python, not by a language model. The Risk Officer uses a free, rule-based mode by default. An optional LLM can help interpret a question, but it does not calculate portfolio metrics.

The app requests about three years of historical daily prices by default. It reports the actual dates and number of observations used. These are not live exchange quotes. If the backend is unavailable, the frontend shows a clearly labeled synthetic demo snapshot.

## Run locally

You need Python 3.12+, Node.js 22.13+, and pnpm. From the project root, use two terminals.

Backend:

~~~bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
~~~

Frontend:

~~~bash
cd frontend
cp .env.example .env.development.local
pnpm install
pnpm dev
~~~

Open http://localhost:3000. The API health check is at http://127.0.0.1:8000/health, and API docs are at http://127.0.0.1:8000/docs. No OpenAI key is needed for the default mode.

You can also start both services with docker compose up --build from the project root.

## Tests

~~~bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests

cd ../frontend
pnpm lint
pnpm build
~~~

## Project layout

- backend/app — API, market-data adapter, risk calculations, optimization, and Risk Officer.
- backend/tests — unit and API tests using synthetic price data.
- frontend/app, frontend/components, frontend/lib — dashboard, charts, and API client.
- docs — longer project notes and resume bullets.

## Notes

Stress tests are simplified scenarios, not predictions or exact replays of past events. Tech exposure and bond duration can use labeled fallback assumptions. Backtest results are hypothetical; they do not include every real-world trading cost or eliminate selection bias. Historical statistics and optimized weights may change when the data changes.

The frontend is hosted on Sites and the Python API on Railway. For a different deployment, set NEXT_PUBLIC_API_URL to the backend's public HTTPS address and CORS_ORIGINS on the backend to the frontend's origin. Never put an API secret in the frontend.

This project is for education and research, not personalized financial advice.
