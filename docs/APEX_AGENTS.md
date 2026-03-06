# APEX Trading System — Agent Registry

Last updated: 2026-03-06

## Core Trading Agents

| Agent | Slug | Role |
|---|---|---|
| India Market Regime Engine | india-market-regime-engine | Classifies NSE market regime every 15 min (VIX, PCR, FII/DII, SGX Nifty, DXY). Writes MARKET_REGIME to memory. |
| Options Strategy Engine | options-strategy-engine | Reads MARKET_REGIME, evaluates 6 strategy types, generates TRADE_SIGNALs with Grade A/B/C, entry/SL/target. |
| Trading Risk Veto Authority | trading-risk-veto-authority | Absolute veto authority. Enforces 2% daily loss limit, 0.5% per-trade risk, Kelly sizing, max 3 concurrent positions. Cannot be overridden. |
| Dhan Paper Trade Engine | dhan-paper-trade-engine | Simulates fills at mid-price via Dhan API. Maintains PAPER_LEDGER with running MTM P&L and SL/target monitoring. PAPER_MODE=true by default. |
| NSE Option Chain Monitor | nse-option-chain-monitor | Polls NSE option chain every 3 sec during market hours. Computes OI buildup, IV rank, gamma walls, PCR, max pain. |
| Sentiment Intelligence Engine | sentiment-intelligence-engine | Scrapes ET, MoneyControl, NSE/BSE, Twitter/X every 5 min. NLP-classifies bullish/bearish/neutral. Writes SENTIMENT_SCORE. |
| Live Trade Performance Monitor | live-trade-performance-monitor | Tracks live Sharpe, Calmar, Sortino, win rate, profit factor. Detects strategy decay via rolling Z-score. |
| Dhan Live Order Executor | dhan-live-order-executor | Full Dhan API v2 live execution engine. Bracket orders, super orders, multi-leg options. Auto-squareoff at 15:10 IST. INACTIVE until PAPER_MODE=false. |

## Intelligence Agents

| Agent | Slug | Role |
|---|---|---|
| Global Macro Intelligence Scanner | global-macro-intelligence-scanner | Pre-session scan: Bloomberg, Reuters, CNBC, FT, Twitter/X. Produces GLOBAL_SENTIMENT score (-1.0 to +1.0). Runs at 02:00 IST and 21:30 IST. |
| NSE Strategy Validation Engine | nse-strategy-validation-engine | Backtests strategy variants against 5yr NSE data with real slippage/brokerage/STT. Monthly walk-forward re-validation. |
| India Trading Central Command | india-trading-central-command | Orchestration hub. Runs morning briefings, routes intraday signals, EOD reconciliation. |

## Learning Agents (NEW)

| Agent | Slug | Role |
|---|---|---|
| APEX Self-Evolution Engine | apex-self-evolution-engine | Post-session learning brain. Runs 7 analysis modules: trade attribution, strategy decay detection, signal calibration, regime accuracy, Kelly fraction evolution, pattern discovery, agent prompt correction. Emails evolution report after every session. |
| APEX Trading Monitor | apex-trading-monitor | Reads APEX memory state and sends richly formatted email updates. Escalates to URGENT on SL risk, VIX spike, or daily loss breach. |

## Trigger Schedule

| Time IST | Trigger | Cron (UTC) |
|---|---|---|
| 02:00 | Asia/Pre-Europe macro scan | `0 20 * * 0-4` |
| 08:30 | Pre-market pipeline (regime + signals + veto) | `0 3 * * 1-5` |
| 09:00 | Morning briefing email | `0 3 * * 1-5` |
| 09:15–15:30 | 15-min regime + signal loop | `*/15 9-15 * * 1-5` |
| 09:15–15:30 | 15-min live channel updates | `*/15 9-15 * * 1-5` |
| 09:15–15:30 | 15-min email monitor | `*/15 9-15 * * 1-5` |
| 15:30 | EOD reconciliation — close all positions | `0 10 * * 1-5` |
| 16:00 | Self-evolution + learning cycle | `0 10 * * 1-5` |
| 21:30 | US market open macro scan | `0 16 * * 1-5` |

## Memory Keys (Shared State)

| Key | Written By | Read By |
|---|---|---|
| MARKET_REGIME | india-market-regime-engine | options-strategy-engine, trading-risk-veto-authority, apex-trading-monitor |
| TRADE_SIGNALS | options-strategy-engine | trading-risk-veto-authority |
| APPROVED_SIGNALS | trading-risk-veto-authority | dhan-paper-trade-engine, apex-trading-monitor |
| VETO_REPORT | trading-risk-veto-authority | apex-self-evolution-engine |
| PAPER_LEDGER | dhan-paper-trade-engine | apex-trading-monitor, trading-risk-veto-authority, apex-self-evolution-engine |
| PAPER_STATS | dhan-paper-trade-engine | apex-self-evolution-engine |
| EXECUTION_LOG | dhan-paper-trade-engine | apex-self-evolution-engine |
| GLOBAL_SENTIMENT | global-macro-intelligence-scanner | india-market-regime-engine |
| GLOBAL_SENTIMENT_ASIA | global-macro-intelligence-scanner | india-market-regime-engine |
| GLOBAL_SENTIMENT_USOPEN | global-macro-intelligence-scanner | india-market-regime-engine |
| GLOBAL_SENTIMENT_COMPOSITE | global-macro-intelligence-scanner | india-market-regime-engine, apex-15-min-live-update-to-channel |
| SENTIMENT_SCORE | sentiment-intelligence-engine | india-trading-central-command |
| OPTIONS_STATE | nse-option-chain-monitor | options-strategy-engine |
| EVOLUTION_LOG | apex-self-evolution-engine | apex-trading-monitor |
| STRATEGY_UPDATES | apex-self-evolution-engine | options-strategy-engine |
| CALIBRATION | apex-self-evolution-engine | trading-risk-veto-authority |

## Paper vs Live Mode

- **Current mode: PAPER** — all trades are simulated via dhan-paper-trade-engine
- To go live: set `PAPER_MODE=false` in APEX_TRADING memory — dhan-live-order-executor takes over
- Risk rules apply equally in both modes
