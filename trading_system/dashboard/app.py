"""
APEX Dashboard — Streamlit-based real-time monitoring dashboard.
Displays live signals, portfolio status, agent health, and performance metrics.
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict

try:
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    import httpx
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


API_BASE = "http://localhost:8000"


def fetch(endpoint: str, default: Any = {}) -> Any:
    try:
        resp = httpx.get(f"{API_BASE}{endpoint}", timeout=3)
        return resp.json()
    except Exception:
        return default


def main():
    if not STREAMLIT_AVAILABLE:
        print("Install: pip install streamlit plotly httpx")
        return

    st.set_page_config(
        page_title="APEX Trading Intelligence",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---- Sidebar ----
    st.sidebar.title("APEX Trading System")
    st.sidebar.markdown("**Indian & Global AI Trading Intelligence**")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (5s)", value=True)
    page = st.sidebar.selectbox(
        "View", ["Dashboard", "Signals", "Portfolio", "Risk", "Performance", "Agents"]
    )

    if page == "Dashboard":
        _render_dashboard()
    elif page == "Signals":
        _render_signals()
    elif page == "Portfolio":
        _render_portfolio()
    elif page == "Risk":
        _render_risk()
    elif page == "Performance":
        _render_performance()
    elif page == "Agents":
        _render_agents()

    if auto_refresh:
        time.sleep(5)
        st.rerun()


def _render_dashboard():
    st.title("APEX — Live Trading Dashboard")
    status = fetch("/api/v1/system/status")
    portfolio = fetch("/api/v1/portfolio")
    risk = fetch("/api/v1/risk/status")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("System Status", status.get("status", "—"))
    with col2:
        st.metric("Capital", f"₹{portfolio.get('capital', 0):,.0f}")
    with col3:
        daily_pnl = portfolio.get("daily_pnl", 0)
        st.metric("Daily P&L", f"₹{daily_pnl:,.0f}", delta=f"{daily_pnl:+,.0f}")
    with col4:
        kill = risk.get("kill_switch_active", False)
        st.metric("Kill Switch", "ACTIVE" if kill else "OFF")

    st.subheader("Signal Summary")
    signals = fetch("/api/v1/signals/latest")
    summary = signals.get("summary", {})
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Bullish Agents", summary.get("bullish", 0))
    with sc2:
        st.metric("Bearish Agents", summary.get("bearish", 0))
    with sc3:
        st.metric("Neutral Agents", summary.get("neutral", 0))


def _render_signals():
    st.title("Agent Signals")
    data = fetch("/api/v1/signals/latest", {"signals": []})
    signals = data.get("signals", [])
    if signals:
        df = pd.DataFrame(signals)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No signals yet. System initialising...")


def _render_portfolio():
    st.title("Portfolio")
    portfolio = fetch("/api/v1/portfolio")
    positions = portfolio.get("open_positions", [])
    if positions:
        df = pd.DataFrame(positions)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No open positions.")


def _render_risk():
    st.title("Risk Monitor")
    risk = fetch("/api/v1/risk/status")
    limits = risk.get("limits", {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Daily Loss %", f"{risk.get('daily_loss_pct', 0):.2f}%",
                  delta_color="inverse")
        st.metric("Drawdown %", f"{risk.get('drawdown_pct', 0):.2f}%",
                  delta_color="inverse")
    with col2:
        st.metric("Open Positions", risk.get("positions", 0))
        st.metric("Max Positions", limits.get("max_positions", 6))


def _render_performance():
    st.title("Performance")
    hist = fetch("/api/v1/performance/history?days=30", {"equity_curve": []})
    equity = hist.get("equity_curve", [])
    if equity:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=equity, mode="lines", name="Equity"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No performance history yet.")


def _render_agents():
    st.title("Agent Network")
    data = fetch("/api/v1/agents/status", {"agents": []})
    agents = data.get("agents", [])
    if agents:
        df = pd.DataFrame(agents)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No agent data.")


if __name__ == "__main__":
    main()
