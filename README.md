# APEX Trading Intelligence System
### Renaissance-Grade Multi-Agent AI Trading System — Indian & Global Markets

---

## Overview

APEX is an institutional-grade autonomous trading intelligence system built on a 20-agent AI network.
It trades Indian markets (NSE/BSE — equities, F&O, indices) and global markets (US, crypto, commodities, forex)
simultaneously, with every decision requiring multi-agent consensus and hard risk enforcement.

Modeled after the internal architecture of Renaissance Technologies, Two Sigma, and D.E. Shaw.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     APEX TRADING SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: DATA INFRASTRUCTURE                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐    │
│  │ TimescaleDB  │ │    Kafka     │ │       Redis          │    │
│  │ (tick store) │ │ (signal bus) │ │   (hot cache)        │    │
│  └──────────────┘ └──────────────┘ └──────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: AGENT NETWORK (20 Agents)                             │
│                                                                 │
│  Market Data (3)    Quant Engine (5)    Macro (4)               │
│  ├ IndianMarket     ├ TechnicalAnalysis  ├ Fundamental          │
│  ├ GlobalMarket     ├ AlgoStrategy       ├ FIIDIIFlow           │
│  └ Commodities      ├ OptionsDerivs      ├ RBIIndianMacro       │
│                     ├ MarketRegime*      └ GlobalMacro           │
│                     └ SGXPreMarket*                              │
│                                                                 │
│  Sentiment (3)      Risk & Portfolio (4)                        │
│  ├ IndianNews       ├ RiskManagement (VETO)                     │
│  ├ GlobalNews       ├ VolatilityKillSwitch*                     │
│  └ Sentiment        ├ PortfolioManager                          │
│                     └ SlippageCostSim*                          │
│                                                                 │
│  Expiry (1)*        (* = NEW agents from research)             │
│  └ ZeroDTEExpiry                                                │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: THE BRAIN                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  InterAgentSignalBus  →  ConflictDetector               │   │
│  │       ↓                                                 │   │
│  │  MasterDecisionMaker  →  LearningEngine                 │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: EXECUTION                                             │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  Backtesting     │  │  Order Mgmt     │  │  Broker API  │  │
│  │  (VectorBT +     │  │  System (OMS)   │  │  (Zerodha    │  │
│  │   NautilusTrader)│  │  VWAP/TWAP      │  │   Kite)      │  │
│  └──────────────────┘  └─────────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: CONTROL PLANE                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  FastAPI        │  │  Dashboard       │  │  Alerts      │  │
│  │  REST + WS      │  │  (HTML/JS)       │  │  (WA/SMS)    │  │
│  └─────────────────┘  └──────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## What This System Trades

| Asset Class        | Instruments                                              |
|--------------------|----------------------------------------------------------|
| Indian Indices     | Nifty 50, Bank Nifty, Finnifty, Midcap Nifty, Sensex F&O |
| Indian Stocks      | 1200+ NSE/BSE stocks — intraday, positional, delivery    |
| Indian Commodities | Gold, Crude (MCX), Agri futures (NCDEX)                 |
| Global Signals     | S&P 500, NASDAQ, Nikkei, SGX Nifty (macro signals)      |
| Forex              | USD/INR, DXY (hedging + macro signal)                   |
| Crypto             | BTC/ETH (risk-on/off sentiment signal)                  |

---

## Core Principles

1. **No single-agent decisions** — minimum 3-agent consensus required for any trade
2. **Risk Agent has absolute VETO** — no position breaches risk limits, ever
3. **Full reasoning chain** — Decision Maker shows complete logic, not a black box
4. **Regime-aware** — strategies switch based on trending/ranging/high-vol detection
5. **India-specific intelligence** — FII/DII flows, RBI policy, SGX Nifty, F&O expiry dynamics
6. **Global macro chain** — Fed → DXY → FII → INR → RBI → India market fully modeled
7. **Self-improving** — Decision Maker reweights agents based on historical win rate

---

## Directory Structure

```
trading_system/
├── agents/                 # All 20 agent implementations
│   ├── layer1_market_data/ # Indian, Global, Commodities, SGX agents
│   ├── layer2_quant/       # Technical, Algo, Options, Regime agents
│   ├── layer3_fundamental/ # Fundamental, FII/DII, RBI, GlobalMacro agents
│   ├── layer4_sentiment/   # News, Sentiment, ZeroDTE agents
│   ├── layer5_risk/        # Risk, VIX KillSwitch, Portfolio, Slippage agents
│   └── layer6_brain/       # SignalBus, ConflictDetector, DecisionMaker, Learner
├── core/                   # Shared models, config, base classes
│   ├── signal_schema.py    # Standardized agent signal format
│   ├── config.py           # System-wide configuration
│   ├── base_agent.py       # Base class all agents inherit
│   └── constants.py        # NSE symbols, expiry calendars, thresholds
├── data/                   # Data infrastructure
│   ├── schema.sql          # TimescaleDB schema
│   ├── kafka_config.py     # Kafka topics and producer/consumer setup
│   ├── redis_config.py     # Redis cache configuration
│   └── connectors/         # Zerodha, Upstox, YFinance, global data connectors
├── execution/              # Order management and broker integration
│   ├── oms.py              # Order Management System
│   ├── kite_broker.py      # Zerodha Kite API integration
│   ├── smart_router.py     # VWAP/TWAP smart order routing
│   └── pre_trade_risk.py   # Pre-trade risk validation
├── risk/                   # Hard risk enforcement (separate from Risk Agent)
│   ├── circuit_breaker.py  # Hard stops — cannot be overridden
│   ├── var_engine.py       # VaR/CVaR calculation engine
│   ├── stress_test.py      # Scenario stress testing
│   └── margin_monitor.py   # Real-time margin monitoring
├── backtesting/            # Strategy validation engine
│   ├── vectorbt_engine.py  # Fast vectorized backtesting
│   ├── nautilus_engine.py  # Production-parity event-driven backtesting
│   ├── walk_forward.py     # Walk-forward validation
│   ├── monte_carlo.py      # Monte Carlo simulation (10,000 scenarios)
│   └── metrics.py          # Sharpe, MaxDD, WinRate, ProfitFactor
├── dashboard/              # Monitoring and control UI
│   ├── app.py              # FastAPI application
│   ├── routes/             # REST API routes
│   ├── websocket.py        # Real-time signal streaming
│   ├── static/             # HTML/CSS/JS dashboard
│   └── alerts.py           # WhatsApp/SMS/email alerting
├── infrastructure/         # Deployment and operations
│   ├── docker-compose.yml  # Full stack orchestration
│   ├── kafka/              # Kafka + Zookeeper config
│   ├── timescaledb/        # DB init scripts
│   └── redis/              # Redis config
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── Makefile                # Build, run, test commands
└── README.md               # This file
```

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in your API keys in .env

# 2. Start infrastructure
make infra-up

# 3. Initialize database
make db-init

# 4. Run backtesting validation
make backtest

# 5. Start paper trading (no real money)
make paper-trade

# 6. Start live trading (real money — ensure backtest passed)
make live-trade

# 7. Open dashboard
open http://localhost:8080
```

---

## Tech Stack

| Component         | Technology                                    |
|-------------------|-----------------------------------------------|
| Agent Framework   | AutoGen v0.4 (Microsoft)                      |
| Backtesting       | VectorBT (research) + Nautilus Trader (prod)  |
| Time-Series DB    | TimescaleDB (PostgreSQL extension)            |
| Signal Bus        | Apache Kafka + Zookeeper                      |
| Hot Cache         | Redis                                         |
| API Framework     | FastAPI + Uvicorn                             |
| Indian Data       | Zerodha Kite API (primary), Upstox (fallback) |
| Global Data       | Yahoo Finance, Alpha Vantage, Polygon.io      |
| Technical Library | pandas-ta, TA-Lib, scipy                      |
| ML/AI             | scikit-learn, XGBoost, PyTorch (regime ML)    |
| Containerization  | Docker + Docker Compose                       |
| Monitoring        | Prometheus + Grafana (optional)               |

---

## Risk Warnings

- This system is for educational and research purposes
- Paper trade extensively before any live deployment
- Never risk capital you cannot afford to lose
- Indian markets have specific SEBI regulations — ensure compliance
- Past backtest performance does not guarantee future results

---

*Built by APEX Quant Systems — Inspired by Renaissance Technologies, Two Sigma, D.E. Shaw*
