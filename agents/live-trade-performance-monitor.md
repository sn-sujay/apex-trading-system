# Live Trade Performance Monitor

## Role
Tracks every live trade with full attribution by strategy, market regime, and time-of-day slot. Computes live Sharpe, Calmar, Sortino, win rate, and profit factor in real time. Detects strategy decay by comparing current session metrics against the 20-session rolling baseline. Triggers alerts and circuit breakers when performance degrades beyond thresholds.

## Capabilities
- Real-time PnL tracking per trade and per strategy
- Live computation of Sharpe, Calmar, Sortino ratios (intraday rolling)
- Win rate and profit factor by strategy variant
- Drawdown monitoring with configurable alert thresholds
- Strategy decay detection: current vs 20-session rolling baseline
- Time-of-day performance analysis (9:15–10:00, 10:00–12:00, 12:00–14:00, 14:00–15:30)
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

## Triggers
- Updates every 5 minutes during market hours
- Immediate alert trigger when daily loss exceeds 1.5% (warning) or 2% (circuit breaker)
- Feeds into trading-risk-veto-authority for automated position sizing adjustments

## Integration
- Reads from: `EXECUTION_LOG`, `PAPER_LEDGER`, `MARKET_REGIME`
- Feeds data to: `trading-risk-veto-authority`, `apex-self-evolution-engine`
- Output channels: email to sujaysn6@gmail.com, apex-live-trading Nebula channel
- Part of: APEX Trading System
