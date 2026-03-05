"""
FastAPI server factory for the APEX Trading System REST API.
Provides system status, signal feed, portfolio state, and manual override endpoints.
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Any

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


def create_app(trading_system: Any = None) -> Any:
    if not HAS_FASTAPI:
        raise ImportError("fastapi and uvicorn are required: pip install fastapi uvicorn")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.trading_system = trading_system
        yield
        # Cleanup on shutdown
        if trading_system and hasattr(trading_system, 'shutdown'):
            await trading_system.shutdown()

    app = FastAPI(
        title="APEX Trading System API",
        description="20-agent autonomous Indian equity trading system",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routes import register_routes
    register_routes(app)

    return app


def run_server(app: Any, host: str = "0.0.0.0", port: int = 8000):
    if not HAS_FASTAPI:
        raise ImportError("fastapi and uvicorn required")
    uvicorn.run(app, host=host, port=port, log_level="info")
