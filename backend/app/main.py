"""FastAPI entrypoint for the RiskLens deterministic analytics service."""

from __future__ import annotations

import os
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.backtest import router as backtest_router
from app.api.optimization import router as optimization_router
from app.api.portfolio import router as portfolio_router
from app.api.stress import router as stress_router
from app.api.var_backtest import router as var_backtest_router
from app.models.responses import HealthResponse

APP_VERSION = "0.6.0"

app = FastAPI(
    title="RiskLens API",
    version=APP_VERSION,
    description="Deterministic portfolio risk analytics. Numerical outputs are never produced by an LLM.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(portfolio_router)
app.include_router(stress_router)
app.include_router(ai_router)
app.include_router(optimization_router)
app.include_router(backtest_router)
app.include_router(var_backtest_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness endpoint for local development and deployment platforms."""

    # Only expose an explicitly configured full commit SHA, never arbitrary
    # environment contents. This is release metadata, not artifact attestation.
    configured_revision = os.getenv("RISKLENS_REVISION", "").strip()
    revision = (
        configured_revision.lower()
        if re.fullmatch(r"[0-9a-fA-F]{40}", configured_revision)
        else None
    )
    return HealthResponse(
        status="ok", service="risklens-api", version=APP_VERSION, revision=revision
    )
