"""
FastAPI Control Plane — REST API + WebSocket streaming for the APEX Trading System.
Provides live system state, signal feeds, portfolio updates, and manual override controls.
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def create_app() -> FastAPI:
    app = FastAPI(
        title="APEX Trading Intelligence System",
        description="Indian & Global AI Trading Intelligence — Control Plane",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- WebSocket manager ----
    class ConnectionManager:
        def __init__(self):
            self.active: List[WebSocket] = []

        async def connect(self, ws: WebSocket):
            await ws.accept()
            self.active.append(ws)

        def disconnect(self, ws: WebSocket):
            self.active.remove(ws)

        async def broadcast(self, data: Dict):
            msg = json.dumps(data)
            dead = []
            for ws in self.active:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active.remove(ws)

    manager = ConnectionManager()

    # ---- Models ----
    class KillSwitchRequest(BaseModel):
        action: str  # "HALT" or "RESUME"
        reason: Optional[str] = None

    class ManualOverrideRequest(BaseModel):
        symbol: str
        direction: str  # BUY / SELL / CLOSE
        quantity: int
        reason: str

    # ---- Routes ----
    @app.get("/health")
    async def health():
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/api/v1/system/status")
    async def system_status():
        return {
            "system": "APEX",
            "status": "RUNNING",
            "kill_switch_active": False,
            "agents_online": 20,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/v1/signals/latest")
    async def get_latest_signals():
        return {
            "signals": [],
            "summary": {"bullish": 0, "bearish": 0, "neutral": 0},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/v1/portfolio")
    async def get_portfolio():
        return {
            "capital": 1_000_000,
            "open_positions": [],
            "daily_pnl": 0,
            "unrealised_pnl": 0,
        }

    @app.get("/api/v1/risk/status")
    async def get_risk_status():
        return {
            "kill_switch_active": False,
            "daily_loss_pct": 0.0,
            "drawdown_pct": 0.0,
            "positions": 0,
            "limits": {
                "max_daily_loss_pct": 1.5,
                "max_drawdown_pct": 8.0,
                "max_positions": 6,
            },
        }

    @app.post("/api/v1/risk/kill_switch")
    async def toggle_kill_switch(req: KillSwitchRequest):
        if req.action not in ("HALT", "RESUME"):
            raise HTTPException(400, "action must be HALT or RESUME")
        return {
            "action": req.action,
            "reason": req.reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.post("/api/v1/trade/override")
    async def manual_override(req: ManualOverrideRequest):
        return {
            "status": "ACCEPTED",
            "order": req.dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/v1/performance/today")
    async def performance_today():
        return {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "net_pnl": 0,
            "gross_pnl": 0,
        }

    @app.get("/api/v1/performance/history")
    async def performance_history(days: int = 30):
        return {"days": days, "equity_curve": [], "daily_pnl": []}

    @app.websocket("/ws/signals")
    async def ws_signals(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    @app.websocket("/ws/portfolio")
    async def ws_portfolio(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                await asyncio.sleep(1)
                await websocket.send_json({"type": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()})
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    return app


app = create_app()
