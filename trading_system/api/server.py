"""
FastAPI server factory for the APEX Trading System REST API.
Exposes endpoints for signals, positions, orders, backtests, and system health.
"""
from __future__ import annotations
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router


def create_app(title: str = "APEX Trading System API", version: str = "1.0.0") -> FastAPI:
    app = FastAPI(
        title=title,
        version=version,
        description="Multi-agent AI trading system for Indian equity F&O markets",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": version}

    return app


app = create_app()
