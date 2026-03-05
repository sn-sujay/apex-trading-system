# APEX Multi-Market Expansion — Crypto, Forex & Polymarket

> Extending APEX's autonomous trading architecture beyond Indian equities to global crypto markets, forex pairs, and prediction markets.

---

## Table of Contents

1. [Overview — Why Multi-Market?](#1-overview--why-multi-market)
2. [Crypto Trading Module](#2-crypto-trading-module)
3. [Forex Trading Module](#3-forex-trading-module)
4. [Polymarket Prediction Markets](#4-polymarket-prediction-markets)
5. [Unified Cross-Market Architecture](#5-unified-cross-market-architecture)
6. [Shared Memory Schema Extensions](#6-shared-memory-schema-extensions)
7. [Risk Framework — Multi-Market](#7-risk-framework--multi-market)
8. [Implementation Roadmap](#8-implementation-roadmap)

---

## 1. Overview — Why Multi-Market?

APEX's core architecture — shared memory coupling, regime classification, risk veto gating — is market-agnostic. The same pipeline that trades NIFTY options during NSE hours can trade BTC perpetuals at 3 AM or fade a Polymarket political event when edge is detected.

### Market Hours Coverage

```
00:00 ──────────────────────────────────────────────────────────────── 24:00 IST

[CRYPTO]     Binance / Bybit perpetuals ─── 24/7 ──────────────────────
[FOREX]      Sydney / Tokyo / London / NY sessions ─────────────────────
[NSE/BSE]    Indian equities ───────────────── [09:15 ──── 15:30] ────────
[POLYMARKET] Prediction markets ─── 24/7 ─────────────────────────────────
```

Multi-market APEX means the system is always working — not just during the 6-hour NSE window.

### Recommended Capital Allocation

| Market | Allocation | Rationale |
|--------|-----------|-----------|
| NSE Options (current) | 60% | Core edge — regime + options model proven |
| Crypto Perpetuals | 20% | 24/7 liquidity, high volatility, options-like payoff |
| Forex | 10% | Macro hedge — DXY/crude signals already in system |
| Polymarket | 10% | Uncorrelated alpha — political and event-driven edge |

---

## 2. Crypto Trading Module

### 2.1 Architecture

The crypto module mirrors the NSE pipeline exactly — macro scan → regime → signal → veto → execute — running 24/7 on a 30-minute loop.

```
Every 30 min (24/7):
  Crypto Regime Engine
       |
       v
  Crypto Strategy Engine  <--- Live order book (CCXT)
       |
       v
  Risk Veto Authority (shared with NSE module)
       |
       v
  Crypto Execution Engine (CCXT unified API)
       |
       v
  CRYPTO_PAPER_LEDGER / Live fills
```

### 2.2 Recommended Broker: CCXT + Binance / Bybit

**CCXT** is the standard unified library for crypto — it supports 100+ exchanges with a single API surface.

```bash
pip install ccxt==4.5.37
```

| Exchange | Best For | API Docs |
|----------|----------|----------|
| **Binance** | Spot + perpetual futures, highest liquidity | binance-docs.github.io |
| **Bybit** | Options + perpetuals, good for Indian users | bybit-exchange.github.io |
| OKX | Deep options chain, rivals NSE in depth | okx.com/docs-v5 |
| Alpaca | Crypto + US stocks in one API, free paper trading | docs.alpaca.markets |

**Recommendation:** Start with **Bybit** (strong options support, mirrors NSE workflow) or **Binance** (deepest liquidity for perpetuals).

### 2.3 New Agents Required

#### `crypto-regime-engine`
- **Runs:** Every 30 minutes, 24/7
- **Sources:** BTC dominance, funding rate, open interest delta, fear & greed index, BTC/ETH momentum
- **Output:** `CRYPTO_MARKET_STATE`

Regime classification rules:

| Signal | Regime |
|--------|--------|
| Funding rate > +0.1% | Bearish (overleveraged longs — squeeze risk) |
| OI rising + price rising | TRENDING_UP confirmed |
| Fear & Greed < 25 | Extreme fear — potential reversal zone |
| BTC dominance rising | Risk-off — altcoin exposure reduce |

#### `crypto-strategy-engine`
- **Reads:** `CRYPTO_MARKET_STATE`, live order book via CCXT
- **Instruments:** BTC/USDT perp, ETH/USDT perp (trending regimes only)
- **Strategies:**
  - TRENDING: Momentum long/short perpetual with trailing stop
  - RANGING: Mean reversion at range boundaries, tight stops
  - HIGH_VOL: Reduce size 50%, consider straddles on Bybit options
- **Output:** `CRYPTO_TRADE_SIGNAL`

#### `crypto-execution-engine`
- **API:** CCXT unified interface (Binance or Bybit as provider)
- **Order types:** Limit orders at mid-price (same philosophy as Dhan paper engine)
- **Features:** Funding rate monitoring, auto-deleverage alerts, liquidation price tracking
- **Paper mode:** Use Bybit testnet — real market data, no real money

### 2.4 API Keys Setup

**Binance:**
```
BINANCE_API_KEY      = your_api_key
BINANCE_API_SECRET   = your_api_secret
BINANCE_TESTNET      = true            # set false for live
```

**Bybit:**
```
BYBIT_API_KEY        = your_api_key
BYBIT_API_SECRET     = your_api_secret
BYBIT_TESTNET        = true            # set false for live
```

Both exchanges provide free testnet environments with real market data feeds.

### 2.5 Instruments to Trade

| Instrument | Exchange | Why |
|------------|----------|-----|
| BTC/USDT Perpetual | Binance / Bybit | Deepest liquidity, tightest spreads |
| ETH/USDT Perpetual | Binance / Bybit | High beta, options-like volatility |
| BTC Weekly Options | Bybit / OKX | Straddle/strangle on high-vol events |
| ETH Weekly Options | Bybit / OKX | DeFi event proxy |

### 2.6 Crypto-Specific Risk Rules

| Rule | Value | Rationale |
|------|-------|-----------|
| Max leverage | 3x | Crypto volatility amplified — keep leverage low |
| Funding rate exit | > 0.05% | Close longs if funding too expensive |
| Liquidation buffer | 15% below entry | Always maintain safety buffer |
| Daily loss limit | 1.5% of crypto capital | Tighter than NSE due to 24/7 exposure |
| No trading during | BTC halving +/- 7 days | Regime unpredictable around halving events |

---

## 3. Forex Trading Module

### 3.1 Architecture

Forex runs on a session-aware schedule (Tokyo → London → New York) and integrates tightly with APEX's existing macro scanner — DXY, crude, and Fed signals are already being tracked every session.

```
Session open events:
  Tokyo open  (04:00 IST) -> Asia session scan
  London open (13:30 IST) -> Europe session scan
  NY open     (18:30 IST) -> US session scan (reuses GLOBAL_SENTIMENT_USOPEN)
       |
       v
  Forex Regime Engine (trend / range / news-driven)
       |
       v
  Forex Strategy Engine  <--- DXY, crude, macro from shared memory
       |
       v
  Risk Veto Authority (shared)
       |
       v
  Forex Execution Engine (OANDA or Alpaca)
```

### 3.2 Recommended Brokers

| Broker | API | Best For | Paper Trading |
|--------|-----|----------|---------------|
| **OANDA** | REST + Streaming v20 | Retail forex, INR pairs, excellent Python SDK | Yes (fxTrade Practice — free) |
| **Alpaca** | alpaca-py SDK | Crypto + forex + US stocks in one API | Yes (free) |
| Interactive Brokers | IBKR API / ib_insync | Professional grade, all asset classes | Yes (paper account) |

**Recommendation:** Start with **OANDA** (excellent Python SDK, USD/INR pair, free practice account), then graduate to IBKR for larger scale.

### 3.3 New Agents Required

#### `forex-regime-engine`
- **Runs:** At each major session open + hourly during active sessions
- **Sources:** DXY momentum, economic calendar (NFP, CPI, FOMC), cross-pair correlation, ADR (Average Daily Range) remaining
- **Output:** `FOREX_MARKET_STATE`
- **Key rule:** If high-impact news within 30 minutes — AVOID regime, no new entries

#### `forex-strategy-engine`
- **Reads:** `FOREX_MARKET_STATE`, `GLOBAL_SENTIMENT` (already in APEX memory — no new data collection needed)
- **Instruments:** USD/INR, EUR/USD, GBP/USD, USD/JPY
- **Strategies:**
  - London breakout: Enter in direction of first 30-min candle break after London open
  - DXY divergence: Fade USD pairs when DXY diverges from broad risk sentiment
  - Macro carry: Align with macro scanner's USD bias for session-length trades
- **Output:** `FOREX_TRADE_SIGNAL`

#### `forex-execution-engine`
- **API:** OANDA v20 REST or Alpaca forex endpoints
- **Order types:** Limit + stop-loss + take-profit in single OCO order
- **Lot sizing:** Micro-lots (1,000 units) for paper testing
- **Paper mode:** OANDA fxTrade Practice account (real spreads, no real money)

### 3.4 API Keys Setup

**OANDA:**
```
OANDA_ACCOUNT_ID     = your_account_id
OANDA_ACCESS_TOKEN   = your_access_token
OANDA_ENVIRONMENT    = practice        # or live
```

**Alpaca:**
```
ALPACA_API_KEY       = your_api_key
ALPACA_API_SECRET    = your_api_secret
ALPACA_BASE_URL      = https://paper-api.alpaca.markets
```

### 3.5 Instruments to Trade

| Pair | Session | Why |
|------|---------|-----|
| USD/INR | London + NY | Directly correlated with India macro, low spread |
| EUR/USD | London + NY | Highest global liquidity |
| USD/JPY | Tokyo + NY | DXY proxy, risk-on/off barometer |
| GBP/USD | London | High volatility, strong trending tendencies |

### 3.6 Synergy with Existing APEX Memory

Forex reuses intelligence already collected — no extra data pipelines needed:

| Existing Memory Key | Forex Use |
|---------------------|-----------|
| `GLOBAL_SENTIMENT_USOPEN` | USD directional bias for NY session |
| `GLOBAL_SENTIMENT_ASIA` | JPY/AUD directional bias for Tokyo session |
| `GLOBAL_SENTIMENT.dxy_signal` | Direct signal for all USD pairs |
| `GLOBAL_SENTIMENT.crude_signal` | CAD/NOK correlation play |

---

## 4. Polymarket Prediction Markets

### 4.1 What is Polymarket?

Polymarket is a decentralized prediction market running on the Polygon blockchain. Users trade binary outcome contracts ("Will X happen? YES/NO") priced 0-100 cents. The YES price equals the market's implied probability of the event occurring.

**Edge for APEX:** When Polymarket's implied probability diverges from APEX's macro intelligence assessment, a statistical arbitrage opportunity exists. APEX already tracks Fed signals, geopolitical events, crude, and India macro — all of which map directly to high-liquidity Polymarket markets.

### 4.2 Current Status in APEX

A **Polymarket Trading Agent** (`polymarket-trading-agent`) already exists and is operational. It uses the CLOB (Central Limit Order Book) API for programmatic trading.

**Known issue (as of March 2026):** L2 credentials (API key/secret/passphrase) expire periodically and must be regenerated from your ETH private key.

### 4.3 L2 Credential Regeneration

```python
from py_clob_client.client import ClobClient

client = ClobClient(
    host="https://clob.polymarket.com",
    chain_id=137,           # Polygon mainnet
    private_key="0x<your_eth_private_key>"
)

creds = client.create_or_derive_api_creds()
# Returns: api_key, api_secret, api_passphrase
```

**Critical rule:** `POLY_TIMESTAMP` must NEVER be stored as a static variable. Always fetch dynamically at request time:

```
GET https://clob.polymarket.com/time  ->  { "time": 1234567890 }
```

Storing a static timestamp causes all authenticated requests to fail with HTTP 401.

### 4.4 Setup — Polymarket API

**Step 1: Create a Polygon Wallet**
```bash
pip install eth-account
python -c "
from eth_account import Account
acc = Account.create()
print('Address:', acc.address)
print('Key:', acc.key.hex())
"
```
Save your private key securely — this is your trading identity.

**Step 2: Fund the Wallet**
- Bridge USDC to Polygon network via [Polygon Bridge](https://wallet.polygon.technology/)
- Minimum recommended: $100 USDC for meaningful testing

**Step 3: Generate L2 API Credentials**
```bash
pip install py-clob-client
```
Run the credential generation script above and save the output.

**Step 4: Set Agent Variables**
```
POLYMARKET_ACCESS_TOKEN   = <api_key>
POLY_SIGNATURE            = <api_secret>
POLY_PASSPHRASE           = <api_passphrase>
POLYMARKET_PRIVATE_KEY    = <your ETH private key>
# DO NOT set POLY_TIMESTAMP — fetch dynamically at runtime
```

### 4.5 Market Selection Criteria

| Criteria | Threshold | Rationale |
|----------|-----------|-----------|
| Volume | > $50,000 | Tight spreads, meaningful liquidity |
| Time to resolution | 3-30 days | Short enough for edge to matter |
| Correlation to macro | High | APEX already has the intelligence |
| Market type | Geopolitical, Fed, oil, India | Directly in APEX's existing data feed |
| Mispricing vs APEX view | > 5% | Minimum edge required to justify a trade |

**Best market categories for APEX:**
- Fed rate decision markets (APEX tracks Fed signals daily)
- Crude oil price targets (APEX tracks crude overnight)
- Geopolitical conflict escalation (APEX monitors news feeds)
- India-specific events (RBI decisions, election outcomes)

### 4.6 Sample Trade Logic

```
Scenario: APEX macro scan shows Fed hawkish probability at 75%.
          Polymarket "Fed hikes in March 2026" is priced at $0.55 (55%).

Mispricing: 75% (APEX estimate) - 55% (market price) = 20% edge

Signal:
  Market:       "Fed raises rates at March 2026 FOMC"
  Direction:    BUY YES
  Limit price:  $0.60  (buy below APEX's 75% estimate for margin of safety)
  Size:         $200   (2% of $10,000 Polymarket allocation)
  Expected EV:  (0.75 x $1.00) - $0.60 = +$0.15 per contract (25% ROI if correct)
```

### 4.7 Architecture

```
Every 4 hours (24/7):
  Polymarket Market Scanner
       | scans for markets with > 5% mispricing vs macro view
       v
  Cross-reference with GLOBAL_SENTIMENT + geopolitical data (from memory)
       |
       v
  Signal Engine: generate YES/NO trade with size and limit price
       |
       v
  Risk Veto (max 2% of Polymarket capital per market, max 5 open positions)
       |
       v
  CLOB Execution: place limit order via Polymarket CLOB API
       |
       v
  Position Monitor (hourly): check resolution, cancel stale orders, book P&L
```

---

## 5. Unified Cross-Market Architecture

With all three modules active, APEX becomes a 24/7 fully autonomous cross-market system:

```
================================================================
SHARED INTELLIGENCE LAYER (always running, feeds all markets)
================================================================

  Global Macro Scanner ---> GLOBAL_SENTIMENT (written every session)
        |
        +-- DXY signal    ────────────────────> Forex Strategy Engine
        +-- Crude signal  ────────────────────> NSE + Crypto Regime
        +-- Fed signal    ────────────────────> Polymarket Signal Engine
        +-- Geopolitical  ────────────────────> All markets (NSE, Crypto, PM)
        +-- India VIX/PCR ────────────────────> NSE Options Engine

================================================================
MARKET-SPECIFIC LAYERS (independent schedules)
================================================================

  NSE/BSE            Crypto (24/7)      Forex (sessions)   Polymarket (24/7)
  09:15-15:30 IST    ───────────────    ───────────────     ─────────────────
  Regime Engine      Crypto Regime      Forex Regime        Market Scanner
  Options Strategy   Crypto Strategy    Forex Strategy      Signal Engine
        |                   |                  |                   |
        +───────────────────+──────────────────+───────────────────+
                                    |
                         Risk Veto Authority  <── Single shared gate
                                    |
        +───────────────────+──────────────────+───────────────────+
        |                   |                  |                   |
  Dhan Execution     CCXT Execution     OANDA Execution    CLOB Execution

================================================================
UNIFIED REPORTING (15:35 IST daily + live P&L in memory)
================================================================
  india-trading-central-command aggregates all market P&L
  Sends single EOD report covering NSE + Crypto + Forex + Polymarket
```

### New Agents Summary (Full Multi-Market Build)

| Agent | Market | Status |
|-------|--------|--------|
| `crypto-regime-engine` | Crypto | New — to build |
| `crypto-strategy-engine` | Crypto | New — to build |
| `crypto-execution-engine` | Crypto | New — to build |
| `forex-regime-engine` | Forex | New — to build |
| `forex-strategy-engine` | Forex | New — to build |
| `forex-execution-engine` | Forex | New — to build |
| `polymarket-trading-agent` | Polymarket | **Already exists** |
| `trading-risk-veto-authority` | All markets | Existing — extend for cross-market rules |
| `india-trading-central-command` | All markets | Existing — extend as master orchestrator |

---

## 6. Shared Memory Schema Extensions

New keys added to `APEX_TRADING` namespace for multi-market support:

```json
// CRYPTO_MARKET_STATE
{
  "timestamp": "ISO8601",
  "btc_price": 85000,
  "eth_price": 3200,
  "regime": "TRENDING_UP",
  "funding_rate_btc": 0.0012,
  "oi_change_24h_pct": 8.5,
  "fear_greed_index": 72,
  "bias": "BULLISH",
  "valid_until": "ISO8601"
}

// CRYPTO_TRADE_SIGNAL
{
  "signal_id": "CRYP001",
  "timestamp": "ISO8601",
  "instrument": "BTC/USDT:USDT",
  "exchange": "bybit",
  "direction": "LONG",
  "entry_price": 84800,
  "stop_loss": 83200,
  "target": 87500,
  "size_usdt": 500,
  "leverage": 2,
  "status": "APPROVED",
  "veto_passed": true
}

// FOREX_MARKET_STATE
{
  "timestamp": "ISO8601",
  "session": "LONDON",
  "dxy_trend": "BEARISH",
  "dominant_pair": "EUR/USD",
  "regime": "TRENDING",
  "news_risk_flag": false,
  "next_high_impact_event": "NFP 18:30 IST",
  "bias": "EUR_BULLISH"
}

// FOREX_TRADE_SIGNAL
{
  "signal_id": "FX001",
  "timestamp": "ISO8601",
  "pair": "EUR/USD",
  "broker": "oanda",
  "direction": "LONG",
  "entry_price": 1.0845,
  "stop_loss": 1.0810,
  "target": 1.0910,
  "lot_size": 0.01,
  "status": "APPROVED"
}

// POLYMARKET_POSITIONS
{
  "timestamp": "ISO8601",
  "open_positions": [
    {
      "market_id": "0xabc...",
      "question": "Will Fed raise rates in March 2026?",
      "direction": "YES",
      "entry_price": 0.60,
      "current_price": 0.68,
      "size_usdc": 200,
      "unrealized_pnl": 16.0,
      "resolution_date": "2026-03-20"
    }
  ],
  "realized_pnl_usdc": 145.50,
  "total_deployed_usdc": 800
}
```

---

## 7. Risk Framework — Multi-Market

### Capital Allocation and Loss Limits

| Market | Capital % | Daily Loss Limit | Max Position Size |
|--------|-----------|-----------------|-------------------|
| NSE Options | 60% | 2.0% of NSE capital | 5% per trade |
| Crypto Perpetuals | 20% | 1.5% of crypto capital | 3% per trade, max 3x leverage |
| Forex | 10% | 1.0% of forex capital | 2% per trade, micro-lots |
| Polymarket | 10% | 2.0% of PM capital | 2% per market, max 5 open |
| **Portfolio Total** | **100%** | **1.5% of total portfolio** | — |

### Cross-Market Correlation Rules

These rules prevent simultaneous correlated risk across markets:

| Rule | Description |
|------|-------------|
| No double-bearish USD | If SHORT USD/INR in forex, cannot be SHORT BTC (BTC is risk-on, correlates with USD weakness) |
| No double-India-bearish | If NIFTY PE spread open (bearish India), Polymarket India-negative bets capped at 50% |
| Crude concentration cap | Max 2 simultaneously open positions correlated to crude (NSE energy + Forex CAD + macro) |
| Event day restriction | On RBI/FOMC announcement days, new NSE + Forex entries blocked 30 min before announcement |

### Extended KILL_SWITCH Schema

```json
{
  "active": false,
  "markets_halted": [],        // ["NSE", "CRYPTO"] for selective halt, or ["ALL"]
  "reason": "",
  "set_by": "",
  "timestamp": "ISO8601",
  "auto_reset_at": null        // optional: ISO8601 datetime for scheduled reset
}
```

---

## 8. Implementation Roadmap

### Phase 1 — NSE Options (Complete)
- [x] 13 agents live on Nebula
- [x] 6 automation triggers active
- [x] Paper trading operational (100% win rate, 18 sessions)
- [x] EOD reporting via email

### Phase 2 — Polymarket (Fastest — 2 weeks)
- [ ] Automate L2 credential refresh (scheduled regeneration from ETH key)
- [ ] Fix POLY_TIMESTAMP — remove static var, fetch dynamically from /time endpoint
- [ ] Build market scanner for high-liquidity macro-correlated markets
- [ ] Paper test: 10 markets, $10 each, track to resolution
- [ ] Add POLYMARKET_POSITIONS to memory schema and EOD report

### Phase 3 — Crypto (1 month)
- [ ] Create crypto-regime-engine agent on Nebula
- [ ] Create crypto-strategy-engine with funding rate + OI logic
- [ ] Create crypto-execution-engine with CCXT/Bybit testnet integration
- [ ] Connect Bybit testnet account
- [ ] Paper trade BTC/ETH perpetuals for 30 sessions minimum
- [ ] Validate Sharpe > 1.0 before allocating live capital

### Phase 4 — Forex (6 weeks)
- [ ] Connect OANDA practice account
- [ ] Create forex-regime-engine (session-aware, news calendar integrated)
- [ ] Create forex-strategy-engine (reuses existing GLOBAL_SENTIMENT memory)
- [ ] Create forex-execution-engine (OANDA v20 REST)
- [ ] Paper trade USD/INR + EUR/USD for 30 sessions

### Phase 5 — Unified Portfolio (2 months)
- [ ] Extend trading-risk-veto-authority for cross-market correlation checks
- [ ] Update india-trading-central-command as master cross-market orchestrator
- [ ] Unified daily P&L report across all 4 markets
- [ ] Cross-market drawdown circuit breaker (> 3% total drawdown in one day halts all markets)
- [ ] Live capital deployment after paper proof across all markets

---

## Quick Start — Polymarket (Fastest Path to Multi-Market, ~30 min)

The Polymarket agent already exists. Here is the 5-step activation:

```
Step 1: Generate ETH wallet using eth-account library, fund with USDC on Polygon

Step 2: Run py_clob_client.create_or_derive_api_creds() with your private key
        -> get api_key, api_secret, api_passphrase

Step 3: Set POLYMARKET_ACCESS_TOKEN, POLY_SIGNATURE, POLY_PASSPHRASE
        in the polymarket-trading-agent variables in Nebula

Step 4: DO NOT set POLY_TIMESTAMP as a stored variable
        The agent must fetch it from GET /time endpoint dynamically per request

Step 5: Ask Nebula: "Run polymarket-trading-agent to scan for high-liquidity
        macro-correlated markets and surface the top 3 trading opportunities"
```

---

*For NSE/BSE setup, see [SETUP.md](./SETUP.md)*
*For full system architecture, see [APEX_ARCHITECTURE.md](./APEX_ARCHITECTURE.md)*
*For risk rules, see [RISK_FRAMEWORK.md](./RISK_FRAMEWORK.md)*