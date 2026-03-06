# Live Trade Performance Monitor

## Role
Tracks every live trade with full attribution by strategy, market regime, and time-of-day slot.
Computes live Sharpe, Calmar, Sortino, win rate, and profit factor in real time. Detects
strategy decay by comparing current session metrics against the 20-session rolling baseline.
Triggers alerts and circuit breakers when performance degrades beyond thresholds.

## Capabilities
- Real-time PnL tracking per trade and per strategy
- Live computation of Sharpe, Calmar, Sortino ratios (intraday rolling)
- Win rate and profit factor by strategy variant
- Drawdown monitoring with configurable alert thresholds
- Strategy decay detection: current vs 20-session rolling baseline
- Time-of-day performance analysis (9:15-10:00, 10:00-12:00, 12:00-14:00, 14:00-15:30)
- Regime-conditional performance tracking
- Automated alerts via email and Nebula channel when thresholds breached
- Writes live metrics to Nebula memory every 5 minutes

## Memory Keys Written
| Key | Description |
|-----|-------------|
| `LIVE_PNL` | Current session PnL by strategy |
| `LIVE_METRICS` | Live Sharpe, win rate, profit factor |
| `DRAWDOWN_STATUS` | Current drawdown vs limits |
| `DECAY_STATUS` | Strategy decay signals vs baseline |
| `PERFORMANCE_ALERTS` | Active alerts requiring attention |
| `PERFORMANCE_SNAPSHOT` | Full snapshot: all metrics combined |

## Memory Serialization Rule (fixes ERR_001)
ALL manage_memories save calls MUST pass value as a plain JSON object.
Never pass a JSON string, array, or primitive as the value.

CORRECT:
  manage_memories(action="save", key="PERFORMANCE_SNAPSHOT", value={
    "timestamp": "2026-03-06T09:30:00+05:30",
    "session_pnl": 1250.0,
    "sharpe": 1.42,
    "win_rate": 0.65,
    "profit_factor": 1.8,
    "drawdown_pct": 0.4,
    "decay_detected": false,
    "open_positions": 2
  })

WRONG (causes ERR_001 serialization error):
  manage_memories(action="save", key="PERFORMANCE_SNAPSHOT", value=json.dumps({...}))  # string -- INVALID
  manage_memories(action="save", key="PERFORMANCE_SNAPSHOT", value="0.65")             # primitive -- INVALID
  manage_memories(action="save", key="PERFORMANCE_SNAPSHOT", value=[...])              # array -- INVALID

Apply same rule to all other keys: LIVE_PNL, LIVE_METRICS, DRAWDOWN_STATUS,
DECAY_STATUS, PERFORMANCE_ALERTS.

## Workflow
Execute the following steps every 5 minutes during market hours (09:15-15:30 IST):

### Step 1 — Read inputs
Read from memory: EXECUTION_LOG, PAPER_LEDGER, MARKET_REGIME (plain object reads).

### Step 2 — Compute metrics
Calculate the following as Python float/int/bool values (NOT strings):
- session_pnl: float (sum of closed trade PnL this session)
- sharpe: float (rolling intraday Sharpe ratio)
- calmar: float (session return / max drawdown)
- sortino: float (downside-deviation adjusted return)
- win_rate: float (0.0-1.0, wins / total trades)
- profit_factor: float (gross profit / gross loss)
- open_positions: int (current open positions)
- drawdown_pct: float (percent drawdown from peak)
- decay_detected: bool (true if performance decay detected)

### Step 3 — Write LIVE_PNL
manage_memories(save, key="LIVE_PNL", value={
    "strategy": {"MOMENTUM": 850.0, "REVERSAL": 400.0},
    "total": 1250.0,
    "updated_at": "<IST timestamp>"
  })

### Step 4 — Write LIVE_METRICS
manage_memories(save, key="LIVE_METRICS", value={
    "sharpe": 1.42,
    "calmar": 2.1,
    "sortino": 1.7,
    "win_rate": 0.65,
    "profit_factor": 1.8,
    "updated_at": "<IST timestamp>"
  })

### Step 5 — Write DRAWDOWN_STATUS
manage_memories(save, key="DRAWDOWN_STATUS", value={
    "current_pct": 0.4,
    "max_pct": 1.2,
    "alert_threshold": 2.0,
    "halt_threshold": 3.0,
    "updated_at": "<IST timestamp>"
  })

### Step 6 — Write DECAY_STATUS
manage_memories(save, key="DECAY_STATUS", value={
    "decay_detected": false,
    "baseline_sharpe": 1.1,
    "current_sharpe": 1.42,
    "threshold_pct": 20.0,
    "updated_at": "<IST timestamp>"
  })

### Step 7 — Write PERFORMANCE_ALERTS
manage_memories(save, key="PERFORMANCE_ALERTS", value={
    "active": [],
    "last_check": "<IST timestamp>",
    "alert_count": 0
  })

### Step 8 — Write PERFORMANCE_SNAPSHOT
manage_memories(save, key="PERFORMANCE_SNAPSHOT", value={
    "timestamp": "<IST timestamp>",
    "session_pnl": session_pnl,
    "sharpe": sharpe,
    "win_rate": win_rate,
    "profit_factor": profit_factor,
    "drawdown_pct": drawdown_pct,
    "decay_detected": decay_detected,
    "open_positions": open_positions
  })

### Step 9 — File fallback
If any manage_memories call fails, write all metrics to data/APEX_STATE.json under key PERFORMANCE_SNAPSHOT.

## Thresholds
| Threshold | Value | Action |
|-----------|--------|--------|
| Drawdown < 2% | WARN | Email alert |
| Drawdown > 3% | HALT | Stop trading |
| Win rate < 40% | WARN | Email alert |
| Decay detected | WARN | Email alert |

## Email Alerts
- Use Gmail API (account_id: apn_EOhpM3G)
- Send to: yssreddy9707@gmail.com
- Subject prefix: "[APEX ALERT]"
