# APEX Risk Framework

## Core Risk Rules (Hard -- Cannot Be Overridden)

1. No TRADE_SIGNAL valid if GLOBAL_SENTIMENT age > 4 hours
2. No TRADE_SIGNAL valid if MARKET_STATE age > 20 minutes
3. No order reaches Dhan API without TRADE_SIGNAL.status = APPROVED
4. KILL_SWITCH.active = true blocks ALL new approvals immediately
5. Risk Veto checks KILL_SWITCH FIRST before any signal evaluation
6. Max 3 concurrent OPEN EXECUTION_RECORDs at any time
7. Only Central Command can reset KILL_SWITCH
8. No naked options -- ever (hard reject regardless of confidence)
9. Half-Kelly sizing applied to all approved signals
10. Daily loss circuit breaker at -2% of capital

---

## Position Sizing -- Half-Kelly Criterion

Kelly fraction: f* = (bp - q) / b
- b = net odds (target / stop_loss ratio)
- p = estimated win probability (confidence_pct / 100)
- q = 1 - p

Half-Kelly applied: position_size = (f* / 2) * available_capital

**Caps:**
- Per-trade risk floor: 0.1% of capital
- Per-trade risk ceiling: 0.5% of capital
- If Half-Kelly exceeds 0.5% cap, reduce to cap
- If Half-Kelly is below 0.1% floor, reject signal (edge too low)

---

## Daily Loss Circuit Breaker

Threshold: -2% of total capital in a single session

**Trigger sequence:**
1. Performance Monitor detects DAILY_PNL.total_pnl_pct <= -2.0
2. Writes KILL_SWITCH = {active: true, reason: "DAILY_LOSS_LIMIT", activated_by: "live-trade-performance-monitor"}
3. Risk Veto reads KILL_SWITCH on next evaluation -- rejects ALL signals
4. No new positions opened for remainder of session
5. Existing positions continue to be monitored for SL/target
6. KILL_SWITCH persists until Central Command manually resets at next session start

---

## Concurrent Position Cap

Maximum 3 open EXECUTION_RECORDs at any time.

**Evaluation:**
- Risk Veto counts OPEN records in PAPER_LEDGER before approving any new signal
- If count >= 3: reject with reason "MAX_CONCURRENT_POSITIONS"
- This applies even if a new signal has higher confidence than existing positions
- No exception -- even for high-conviction EVENT regime signals

---

## Per-Signal Veto Checklist

Risk Veto Authority runs ALL checks in this order:

| # | Check | Threshold | Action if Fail |
|---|---|---|---|
| 1 | Kill switch active? | active = false | REJECT ALL -- stop here |
| 2 | Daily loss breached? | total_pnl_pct > -2% | REJECT ALL |
| 3 | Concurrent positions? | open_count < 3 | REJECT signal |
| 4 | Confidence threshold? | confidence_pct >= 60 | REJECT signal |
| 5 | Per-trade risk cap? | max_risk_inr <= 0.5% capital | Size down or REJECT |
| 6 | Naked options? | legs must be spread | HARD REJECT |
| 7 | Data freshness? | GLOBAL_SENTIMENT < 4h, MARKET_STATE < 20min | REJECT signal |
| 8 | Kelly sizing valid? | Half-Kelly >= 0.1% floor | REJECT signal |

All 8 must pass. Partial pass = REJECTED.

---

## Strategy Risk by Regime

| Regime | Allowed Strategies | Max New Positions | Notes |
|---|---|---|---|
| TRENDING_UP | Bull Call Spread, Long Call | 2 | Directional only |
| TRENDING_DOWN | Bear Put Spread, Long Put | 2 | Directional only |
| RANGING | Iron Condor, Short Strangle | 2 | Non-directional |
| VOLATILE | Long Straddle, Long Strangle | 1 | Elevated premium -- size down |
| EVENT | All strategies | 1 | Max 1 -- Iran War / macro event mode |
| AVOID | None | 0 | No signals generated |

---

## Kill Switch Triggers

| Trigger | Source | Auto/Manual |
|---|---|---|
| Daily loss >= 2% | Performance Monitor | Auto |
| Manual halt | Central Command | Manual |
| VIX spike > 25 (sudden) | Regime Engine | Auto |
| Dhan API failure x3 | Paper/Live Executor | Auto |
| Exchange circuit breaker | Option Chain Monitor | Auto |

**Reset:** Only `india-trading-central-command` can set KILL_SWITCH.active = false.
Reset occurs at session start (08:00 IST) if reason is not MANUAL_HALT.
MANUAL_HALT requires explicit owner instruction to reset.

---

## Overnight Position Rules

Positions carried overnight are subject to:
- DTE monitoring: positions with DTE <= 5 flagged as CRITICAL
- Gap risk: GLOBAL_SENTIMENT_ASIA scan at 02:00 IST evaluates overnight gap
- If composite sentiment score < -0.5 AND open position is directional: generate conditional exit order for 09:15 IST open
- Cushion monitoring: if spot moves within 20% of short strike, flag for manual review

---

## Charges & Cost Model

Applied to all paper and live fills:

| Cost | Rate |
|---|---|
| Brokerage | Rs 20 per executed order (Dhan flat fee) |
| STT (buy side options) | 0.0125% of premium |
| STT (sell side options on exercise) | 0.125% of intrinsic value |
| Exchange transaction charge | 0.053% of turnover |
| SEBI charges | Rs 10 per crore |
| GST | 18% on brokerage + transaction charges |
| Stamp duty | 0.003% of buy side premium |

Total effective charge per round trip (typical spread): ~Rs 165-200
