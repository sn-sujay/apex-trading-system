"""
API route definitions for APEX Trading System.
Endpoints: health, system status, signals, portfolio, risk, kill-switch, manual override.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


def register_routes(app: Any):
    if not HAS_FASTAPI:
        return

    @app.get("/health")
    async def health():
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/api/v1/status")
    async def system_status():
        ts = app.state.trading_system
        if not ts:
            return {"status": "not_initialised"}
        return {
            "status": "running" if getattr(ts, 'is_running', False) else "stopped",
            "paper_mode": getattr(ts, 'paper_mode', True),
            "market_open": getattr(ts, 'market_open', False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/v1/signals")
    async def get_signals():
        ts = app.state.trading_system
        if not ts or not hasattr(ts, 'signal_bus'):
            return {"signals": [], "summary": {}}
        summary = ts.signal_bus.get_signal_summary()
        signals = [
            {
                "agent": name,
                "direction": sig.direction.value,
                "confidence": sig.confidence,
                "weight": sig.signal_weight,
            }
            for name, sig in ts.signal_bus.get_all_signals().items()
        ]
        return {"signals": signals, "summary": summary}

    @app.get("/api/v1/portfolio")
    async def get_portfolio():
        ts = app.state.trading_system
        if not ts or not hasattr(ts, 'portfolio_manager'):
            return {"portfolio": {}}
        return ts.portfolio_manager.get_portfolio_summary()

    @app.get("/api/v1/risk")
    async def get_risk():
        ts = app.state.trading_system
        if not ts or not hasattr(ts, 'risk_manager'):
            return {"risk": {}}
        rm = ts.risk_manager
        ks = getattr(ts, 'kill_switch', None)
        return {
            "capital": rm.state.capital,
            "daily_pnl": rm.state.daily_pnl,
            "weekly_pnl": rm.state.weekly_pnl,
            "open_positions": len(rm.state.open_positions),
            "kill_switch_active": ks.is_active if ks else False,
            "kill_switch_reason": ks.trigger_reason if ks else None,
        }

    @app.post("/api/v1/kill-switch/activate")
    async def activate_kill_switch():
        ts = app.state.trading_system
        if not ts or not hasattr(ts, 'kill_switch'):
            raise HTTPException(status_code=404, detail="Kill switch not available")
        ts.kill_switch._activate("Manual activation via API")
        return {"activated": True, "reason": "Manual API call"}

    @app.post("/api/v1/kill-switch/reset")
    async def reset_kill_switch():
        ts = app.state.trading_system
        if not ts or not hasattr(ts, 'kill_switch'):
            raise HTTPException(status_code=404, detail="Kill switch not available")
        ts.kill_switch.reset()
        return {"reset": True}

    @app.get("/api/v1/decisions")
    async def get_decisions():
        ts = app.state.trading_system
        if not ts or not hasattr(ts, 'master_decision_maker'):
            return {"decisions": []}
        return {
            "decisions": ts.master_decision_maker._decision_history[-20:]
        }
