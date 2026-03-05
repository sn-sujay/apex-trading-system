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
  Options Strategy Engine  -> TRADE_SIGNAL (PENDING_VETO)
  Risk Veto Authority      -> TRADE_SIGNAL (APPROVED / REJECTED)
  Paper Trade Engine       -> EXECUTION_RECORD + PAPER_LEDGER

LAYER 4 — POSITION MONITOR (Every 5 min)
  Paper Trade Engine       -> SL/Target check -> MTM update -> DAILY_PNL

LAYER 5 — EOD (15:35 IST)
  Performance Monitor      -> DAILY_REPORT
  Central Command          -> Email digest -> SESSION_LOG
```

---

## 3. Agent Network — 13 Agents

| # | Slug | Role | Memory Writes | TTL |
|---|---|---|---|---|
| 1 | india-trading-central-command | Orchestrator, KILL_SWITCH owner | KILL_SWITCH, SESSION_LOG | Manual |
| 2 | global-macro-intelligence-scanner | Macro scan (3 triggers) | GLOBAL_SENTIMENT, _USOPEN, _ASIA | 4h |
| 3 | india-market-regime-engine | VIX/PCR/FII regime classifier | MARKET_STATE | 20min |
| 4 | nse-option-chain-monitor | OI/IV/GEX/Max Pain poller | OPTIONS_STATE | 5min |
| 5 | sentiment-intelligence-engine | ET/MC/Twitter NLP | SENTIMENT_STATE | 10min |
| 6 | options-strategy-engine | Signal generator | TRADE_SIGNAL (PENDING_VETO) | Until exec |
| 7 | trading-risk-veto-authority | 8-point risk gate | TRADE_SIGNAL status, VETO_REPORT | Until exec |
| 8 | dhan-paper-trade-engine | Paper fills, P&L ledger | EXECUTION_RECORD, PAPER_LEDGER | Live |
| 9 | dhan-live-order-executor | Live bracket orders (standby) | EXECUTION_RECORD | Live |
| 10 | live-trade-performance-monitor | Sharpe/Calmar/Sortino, EOD | DAILY_PNL, DAILY_REPORT | Daily |
| 11 | nse-strategy-validation-engine | 5yr backtest gate | STRATEGY_LIBRARY | Permanent |
| 12 | nse-option-chain-monitor | Also standalone poller | OPTIONS_STATE | 5min |
| 13 | polymarket-trading-agent | Prediction market (parallel) | POLYMARKET_* | Live |

---

## 4. Automation Triggers — 6 Scheduled Pipelines

| Trigger Slug | Schedule | IST Time | Steps |
|---|---|---|---|
| apex-daily-session-pipeline | 0 2 * * 1-5 | 08:00 IST | Macro -> Regime -> Signal -> Veto -> Execute -> EOD |
| apex-15-min-regime-signal-loop | 0 9-15 * * 1-5 | Every hour 09:00-15:00 IST | Regime -> Signal -> Veto -> Execute |
| apex-sltarget-monitor-5-min | 0 9-15 * * 1-5 | Every hour market hours | SL/Target check, MTM update |
| apex-eod-reconciliation-1535-ist | 0 10 * * 1-5 | 15:30 IST | Close positions, P&L, email |
| apex-us-market-open-scan-2130-ist | 0 16 * * 1-5 | 21:30 IST | NYSE open macro scan |
| apex-asiapre-europe-scan-0200-ist | 0 20 * * 0-4 | 02:00 IST | SGX/Nikkei/Hang Seng scan |

---

## 5. Signal Flow — End-to-End

```
Global Macro Scanner
  writes GLOBAL_SENTIMENT

India Market Regime Engine
  reads GLOBAL_SENTIMENT
  writes MARKET_STATE (regime + confidence)

NSE Option Chain Monitor
  writes OPTIONS_STATE (OI, IV, GEX, Max Pain)

Sentiment Intelligence Engine
  writes SENTIMENT_STATE (NLP scores)

Options Strategy Engine
  reads GLOBAL_SENTIMENT + MARKET_STATE + OPTIONS_STATE + SENTIMENT_STATE
  selects strategy from regime-sentiment matrix
  builds full leg spec with live LTP from Dhan
  writes TRADE_SIGNAL (status: PENDING_VETO)

Trading Risk Veto Authority
  reads TRADE_SIGNAL
  runs 8-point checklist
  writes TRADE_SIGNAL.status = APPROVED or REJECTED
  writes VETO_REPORT

Dhan Paper Trade Engine
  reads APPROVED_SIGNALS
  fetches live LTP from Dhan API
  simulates fill at mid-price with slippage
  applies charges
  writes EXECUTION_RECORD
  updates PAPER_LEDGER

Live Trade Performance Monitor
  reads all EXECUTION_RECORDs
  computes Sharpe, Calmar, Sortino, win rate
  updates DAILY_PNL
  triggers KILL_SWITCH if loss > 2%

India Trading Central Command
  reads DAILY_REPORT at 15:35 IST
  sends EOD email to sujaysn6@gmail.com
  writes SESSION_LOG
```

---

## 6. Risk Management

See docs/RISK_FRAMEWORK.md for full details.

**Summary:**
- Kill switch: blocks all signals immediately when active
- Circuit breaker: -2% daily loss auto-activates kill switch
- Per-trade risk: 0.5% of capital max (Half-Kelly sizing)
- Concurrent cap: max 3 open positions
- Naked options: hard rejected always
- Data freshness: GLOBAL_SENTIMENT < 4h, MARKET_STATE < 20min required

---

## 7. Performance (Paper Sessions 1-18)

| Metric | Value |
|---|---|
| Sessions completed | 18 |
| Win rate | 100% |
| Latest net P&L | +Rs 4,880.80 (+0.651%) |
| Gross realized | +Rs 6,259.50 |
| Total charges | -Rs 331.70 |
| Risk budget used | 45.9% |
| Current regime | EVENT (0.88) — Iran War Day 6 |
| Open overnight | 2 positions |

---

## 8. Live Trading Activation Checklist

Before switching PAPER_MODE=false:

- [ ] Minimum 30 sessions paper traded
- [ ] Win rate >= 55% sustained
- [ ] Max drawdown < 8% in paper
- [ ] Sharpe >= 1.5 in paper
- [ ] Dhan API credentials tested and valid
- [ ] Capital allocated matches risk parameters
- [ ] KILL_SWITCH tested (manual activation/reset)
- [ ] EOD email confirmed working
- [ ] Regime classification validated vs manual assessment
- [ ] At least 1 full market-crash simulation run

---

*Built with Nebula multi-agent orchestration. All paper trading — PAPER_MODE=true.*
