# APEX Trading System — Complete Architecture Documentation

> **APEX** — Autonomous Prediction & Execution System
> Fully autonomous AI-powered intraday options trading for Indian markets (NSE/BSE)
> Built on Nebula's multi-agent orchestration platform

**Status:** Paper Trading (PAPER_MODE=true) | Sessions Completed: 18 | Win Rate: 100% | Latest Net P&L: +Rs 4,880.80

---

## Table of Contents

1. System Overview
2. High-Level Architecture Diagram
3. Agent Network — 13 Specialized Agents
4. Automation Triggers — 6 Scheduled Pipelines
5. Shared Memory Schema — APEX_TRADING Namespace
6. Signal Flow — End-to-End Pipeline
7. Risk Management Framework
8. Broker & API Integrations
9. Instruments Traded
10. Options Strategy Catalogue
11. Cost & Charges Model
12. Paper Trading Results
13. Live Trading Activation Checklist
14. Roadmap

---

## 1. System Overview

APEX is a zero-human-intervention intraday options trading system that operates 24 hours a day, 7 days a week. It wakes up at 02:00 IST to scan Asian markets overnight, runs a full pre-session intelligence brief at 08:00 IST, executes a 15-minute regime + signal loop throughout the trading day, monitors every open position every 5 minutes, and auto-reconciles at 15:35 IST after market close.

The system is built on a **shared-memory, zero-direct-coupling** architecture. No agent calls another agent directly. Every piece of intelligence, every trade signal, every execution record, and every risk flag is written to the `APEX_TRADING` Nebula shared memory namespace. Downstream agents read from memory, validate freshness, and act accordingly. This makes the system resilient — any agent can fail and restart without cascading failures elsewhere.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| Zero human intervention | All signals, vetoes, and executions are fully automated |
| Memory-first coupling | All inter-agent data flows through shared memory, never direct calls |
| Hard risk gates | Every signal passes a mandatory 8-point veto before reaching the broker |
| Regime-aware | Strategy type is determined by current market regime, not fixed rules |
| Cost-realistic | All paper fills include real brokerage, STT, GST, stamp duty |
| Fail-safe defaults | Any missing/stale data triggers AVOID, never a trade |

---

## 2. High-Level Architecture

```
LAYER 0 — OVERNIGHT INTELLIGENCE
  21:30 IST (NYSE Open)    -> GLOBAL_SENTIMENT_USOPEN
  02:00 IST (Asia Scan)    -> GLOBAL_SENTIMENT_ASIA

LAYER 1 — PRE-SESSION (08:00 IST)
  Global Macro Scanner     -> GLOBAL_SENTIMENT [-1.0 to +1.0]

LAYER 2 — MARKET OPEN (09:00-09:15 IST)
  Regime Engine            -> MARKET_STATE     (TTL: 20min)
  Option Chain Monitor     -> OPTIONS_STATE    (TTL: 5min)
  Sentiment Engine         -> SENTIMENT_STATE  (TTL: 10min)

LAYER 3 — SIGNAL LOOP (Every 15 min, 09:15-15:30 IST)
  Options Strategy Engine  -> TRADE_SIGNAL (new ones only)
  Learning Engine          -> MODEL_STATE_JSON (every 36min)

LAYER 4 — EXECUTION
  Master Decision Maker    -> vetoes signals
  Risk Manager             -> 8-point validation
  Dhan API v2              -> NSE/BSE order execution

LAYER 5 — MANAGEMENT
  Position Monitor         -> every 5min, SL & TP
  EOD Reconciliation       -> 15:35 IST daily
```

---

## 3. Agent Network

| Agent Name | Trigger | Output Key | TTL & MaxOutage |
|------------|---------|------------|------------------|
| Global Macro Scanner | Trigger01 (21:30 IST) | `GLOBAL_SENTIMENT` | 8h / 36h |
| SGX Pre-Market | Trigger02 (08:00 IST) | `SGX_DATA`, `INDEX_OUTLOOK` | 24h / 48h |
| Indian Market Data | Trigger02 (08:00 IST) | `MARKET_DATA` | 24h / 48h |
| FII/DII Flow | Trigger02 (08:00 IST) | `FII_DII_FLOW`, `INSTITUTIONAL_TREND` | 24h / 48h |
| Options & Derivatives | Trigger03 (09:01 IST) | `OPTIONS_STATE` | 5min / 15min |
| Market Regime | Trigger04 (Every 15min) | `MARKET_STATE` | 20min / 60min |
| Technical Analysis | Trigger04 (Every 15min) | `TECHNICAL_SIGNALS` | 20min / 60min |
| Algo Strategy | Trigger04 (Every 15min) | `TARGETS` | 20min / 60min |
| Sentiment & Positioning | Trigger04 (Every 15min) | `SENTIMENT_STATE`, `POSITIONING_DATA` | 20min / 60min |
| Zero-DTE Expiry | Trigger04 (Every 15min) | `ZERO_DTE_SIGNALS` | 20min / 60min |
| Master Decision Maker | Trigger04 (Every 15min) | `TARGETS` | 20min / 60min |
| Order Management System | Trigger04 (Every 15min) | `POSITIONS_JSON` | 20min / 60min |
| Exposure & Risk Management | Trigger05 (Every 5min) | `RISK_STATE` | 10min / 30min |

---

## 4. Automation Triggers

| Trigger | Schedule | Pipeline Steps | Purpose |
|---------|----------|-----------------|---------|
| Trigger01 | 21:30 IST daily | Global Macro — Sentiment | US market open intelligence |
| Trigger02 | 08:00 IST daily | Pre-Session Intelligence Brief | Full morning intel |
| Trigger03 | 09:01 IST daily | Option Chain Refresh | Opening option chain snapshot |
| Trigger04 | Every 15min, 09:15-15:30 IST | Regime + Signal Loop | Core trading loop |
| Trigger05 | Every 5min, 09:15-15:30 IST | Position Monitor | SL, TP trailing, expiry |
| Trigger06 | 15:35 IST daily | EOD Reconciliation | PnL, report, learning |

---

## 5. Shared Memory Schema

All inter-agent state is stored in the `APEX_TRADING` memory namespace:

```
KILL_SWITCH                   # global trading halt flag
GLOBAL_SENTIMENT             # [-1, +1] float
MARKET_STATE                 # JSON: regime, VIX, BankNifty status
OPTIONS_STATE                # JSON: spot, IV params, GD levels
TECHNICAL_SIGNALS            # JSON: entry/exit signals
TRADE_SIGNAL                 # JSON: current trade proposal
POSITIONS_JSON               # JSON: all open positions
PAPER_LEDGER                 # JSON: paper P&L tracker
DAILY_PNL                    # float: realized + unrealized P&L
MODEL_STATE_JSON             # JSON: learning engine weights
```

---

## 6. Signal Flow -- End-to-End

```
[4 agents] -> signals -> SignalBus -> ConflictDetector -> MasterDecisionMaker
                                                               |
                                                      RiskManager (8-point veto)
                                                               |
                                                         DhanExecutor
                                                               |
                                                        OMS (log + track)
```

---

## 7. Risk Management Framework

### 8-Point Veto System

Every trade signal must pass all 8 veto checks before reaching the broker:

| Check | Threshold |
|-------|-----------|
| Kill Switch | Must be OFF |
| Daily P&L loss limit | > -5% of capital |
| IV rank for options | IVR < 80 for new longs |
| Delta neutrality | Portfolio delta < +/- 200 |
| Market regime filter | No new positions in CRASH regime |
| Expiry filter | No new positions in final 30min before expiry |
| Position size cap | Max 5% per leg, 15% per sector |
| Sector exposure | No single sector > 30% of capital |

---

## 8. Broker & API Integrations

| Layer | Service | Purpose | API |
|-------|---------|---------|-----|
| Order Execution | Dhan API v2 | NSE/BSE orders | api.dhan.co |
| Live Data | Dhan API v2 WebSocket | Real-time ticks | Dhan Market Feed |
| Option Chain | Indian API | Instrument snapshots | indianapi.in |
| Historical data | Indian API | OHLCV history | indianapi.in |
| Global macro | Yfinance / AlphaVantage | US, asian indices | /markets |
| Sentiment | StockTwits Whisperer | Social positioning data | whisperer API |
| Alerts | Twilio WhatsApp | Trade notifications | Twilio API |
| Alerts | SendGrid Email | EOD reports | SendGrid API |

---

## 9. Instruments Traded

| Instrument | Type | Exchange | Expiry | Lot Size |
|------------|------|----------|---------|----------|
| NIFTY | Index Options | NSE F&O | Weekly & Monthly | 50 |
| BANKNIFTY | Index Options | NSE F&O | Weekly & Monthly | 15 |
| FINNIFTY | Index Options | NSE F&O | Weekly & Monthly | 40 |
| NIFTY Futures | Futures | NSE F&O | Monthly | 75 |
| BANKNIFTY Futures | Futures | NSE F&O | Monthly | 15 |

---

## 10. Options Strategy Catalogue

| Strategy | Regime | Max Risk | Target P&L |
|----------|--------|----------|------------|
| Bullish Call Spread | UPTREND | Premium paid | 2X risk |
| Bearish Put Spread | DOWNTREND | Premium paid | 2X risk |
| Iron Condor | RANGING | Margin required | Net premium collected |
| Strangle | BREAKOUT | Premium paid | 3X risk |
| Calendar Spread | RANGING | Net debit | 2X risk |
| Protective Put | CRASH | Premium paid | Hedge only |
| Butterfly Spread | RANGING | Net debit | 3X risk |

---

## 11. Cost & Charges Model

Since APEX uses DhanHQ as the primary broker, the following applies:

| Charge | Rate |
|--------|------|
| Brokerage | Flat Rs 20 per order or Lower of 0.03% |
| STT | 0.1% on sell side (equity delivery) |
| GST | 18% on brokerage |
| Stamp Duty | 0.015% on buy side |

---

## 12. Paper Trading Results

| Metric | Value |
|--------|-------|
| Sessions Completed | 18 |
| Win Rate | 100% |
| Latest Net P&L | +Rs 4,880.80 |
| Avg Trade Duration | 35min |
| Max Drawdown | -0.8% |

---

## 13. Live Trading Activation Checklist

- [ ] Paper trading > 20 sessions with > 60% win rate
- [ ] Dhan API v2 Client ID and Access Token configured and tested
- [ ] Risk limits reviewed and set
- [ ] Emergency kill switch tested
- [ ] Alerts (WhatsApp + email) configured
- [ ] Set ENABLE_LIVE_TRADING=true in Nebula secrets

---

## 14. Roadmap

| Phase | Timeline | Feature |
|-------|----------|---------|
| v1.0 | Completed | Paper trading live with 18 sessions |
| v1.1 | Month 2 | Dhan API v2 live order execution |
| v1.2 | Month 3 | Auto-token refresh for Dhan API v2 |
| v2.0 | Month 4+ | Multi-broker fallback execution routing |
