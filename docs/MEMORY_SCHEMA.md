# APEX Trading System -- Shared Memory Schema

All agents read/write exclusively via Nebula shared memory under the `APEX_TRADING` namespace.
No direct agent-to-agent calls. Memory is the single source of truth.

## Read/Write Protocol

- **Write:** `manage_memories(action='save', app='APEX_TRADING', key='KEY_NAME', value='JSON_string')`
- **Read:** `manage_memories(action='list', app='APEX_TRADING')` then parse by key
- All timestamps in IST (Asia/Kolkata, UTC+5:30)
- All agents validate data freshness before consuming (check `generated_at` / `updated_at`)

---

## 1. GLOBAL_SENTIMENT
**Writer:** Global Macro Intelligence Scanner
**Readers:** All agents
**TTL:** 4 hours -- signals rejected if older

```json
{
  "score": "float [-1.0 to +1.0]",
  "label": "STRONGLY_BEARISH | BEARISH | NEUTRAL_BEARISH | NEUTRAL | NEUTRAL_BULLISH | BULLISH | STRONGLY_BULLISH",
  "directional_bias": "LONG | SHORT | NEUTRAL",
  "conviction": "HIGH | MEDIUM | LOW",
  "generated_at": "ISO8601 IST",
  "valid_for_session": "YYYY-MM-DD",
  "fed_signal": "float [-1.0 to +1.0]",
  "us_banking_signal": "float [-1.0 to +1.0]",
  "geopolitical_signal": "float [-1.0 to +1.0]",
  "commodity_signal": "float [-1.0 to +1.0]",
  "risk_appetite_signal": "float [-1.0 to +1.0]",
  "key_headlines": ["string", "string", "string"],
  "banknifty_bias": "BULLISH | BEARISH | NEUTRAL",
  "bankex_bias": "BULLISH | BEARISH | NEUTRAL",
  "confidence_pct": "int [0-100]"
}
```

---

## 2. MARKET_STATE
**Writer:** India Market Regime Engine
**Readers:** Options Strategy Engine, Risk Veto Authority, Central Command
**TTL:** 20 minutes

```json
{
  "regime": "TRENDING_UP | TRENDING_DOWN | RANGING | VOLATILE | EVENT | AVOID",
  "confidence": "float [0.0 to 1.0]",
  "india_vix": "float",
  "pcr": "float",
  "max_pain": "int",
  "fii_net_inr_cr": "float",
  "dii_net_inr_cr": "float",
  "sgx_nifty": "float",
  "dxy": "float",
  "crude_wti": "float",
  "suggested_strategy_type": "DIRECTIONAL | NON_DIRECTIONAL | AVOID",
  "generated_at": "ISO8601 IST",
  "valid_until": "ISO8601 IST"
}
```

---

## 3. OPTIONS_STATE
**Writer:** NSE Option Chain Monitor
**Readers:** Options Strategy Engine
**TTL:** 5 minutes

```json
{
  "instrument": "NIFTY | BANKNIFTY | FINNIFTY | MIDCPNIFTY | BANKEX",
  "spot_price": "float",
  "atm_strike": "int",
  "pcr_live": "float",
  "iv_rank": "float [0-100]",
  "iv_percentile": "float [0-100]",
  "max_pain": "int",
  "gex_walls": {
    "call_wall": "int",
    "put_wall": "int",
    "zero_gamma": "int"
  },
  "oi_buildup": [{"strike": "int", "type": "CE|PE", "oi_change": "int", "signal": "BUILDUP|UNWINDING"}],
  "generated_at": "ISO8601 IST",
  "valid_until": "ISO8601 IST"
}
```

---

## 4. TRADE_SIGNAL
**Writer:** Options Strategy Engine (PENDING_VETO), Risk Veto (APPROVED/REJECTED)
**Readers:** Risk Veto Authority, Paper/Live Executor
**TTL:** Until executed or expired

```json
{
  "signal_id": "string (e.g. SIG001)",
  "instrument": "NIFTY | BANKNIFTY",
  "strategy": "BULL_CALL_SPREAD | BEAR_PUT_SPREAD | IRON_CONDOR | LONG_STRADDLE | LONG_STRANGLE | LONG_PUT_SPREAD | LONG_CALL_SPREAD",
  "legs": [
    {
      "action": "BUY | SELL",
      "strike": "int",
      "option_type": "CE | PE",
      "expiry": "YYYY-MM-DD",
      "quantity": "int (lots)",
      "limit_price": "float",
      "security_id": "string (Dhan security ID)"
    }
  ],
  "net_debit_credit": "float (negative = debit, positive = credit)",
  "stop_loss_price": "float",
  "target_price": "float",
  "max_risk_inr": "float",
  "confidence_pct": "int [0-100]",
  "regime_at_signal": "string",
  "sentiment_at_signal": "float",
  "status": "PENDING_VETO | APPROVED | REJECTED | EXECUTED | EXPIRED",
  "veto_reason": "string | null",
  "generated_at": "ISO8601 IST",
  "approved_at": "ISO8601 IST | null",
  "kelly_position_size_inr": "float | null"
}
```

---

## 5. EXECUTION_RECORD
**Writer:** Dhan Paper Trade Engine / Dhan Live Order Executor
**Readers:** Performance Monitor, Central Command
**TTL:** Permanent (session log)

```json
{
  "execution_id": "string (e.g. EXE001)",
  "signal_id": "string",
  "instrument": "string",
  "strategy": "string",
  "entry_fills": [
    {
      "strike": "int",
      "option_type": "CE | PE",
      "action": "BUY | SELL",
      "fill_price": "float",
      "quantity": "int",
      "fill_time": "ISO8601 IST"
    }
  ],
  "exit_fills": [],
  "status": "OPEN | CLOSED",
  "exit_reason": "STOP_LOSS | TARGET | EOD_SQUAREOFF | MANUAL | null",
  "entry_total_premium": "float",
  "exit_total_premium": "float | null",
  "gross_pnl_inr": "float | null",
  "charges_inr": "float | null",
  "net_pnl_inr": "float | null",
  "paper_mode": "true | false",
  "opened_at": "ISO8601 IST",
  "closed_at": "ISO8601 IST | null"
}
```

---

## 6. PAPER_LEDGER
**Writer:** Dhan Paper Trade Engine
**Readers:** Risk Veto, Performance Monitor, Central Command
**TTL:** Live (updated in real time)

```json
{
  "updated_at": "ISO8601 IST",
  "open_positions": [
    {
      "execution_id": "string",
      "signal_id": "string",
      "instrument": "string",
      "strategy": "string",
      "legs": [],
      "entry_premium": "float",
      "current_premium": "float",
      "stop_loss_price": "float",
      "target_price": "float",
      "mtm_pnl_inr": "float",
      "dte": "int",
      "cushion_pct": "float",
      "status_flags": ["DTE_CRITICAL", "SL_THIN", "HEALTHY"]
    }
  ],
  "closed_trades": [],
  "open_count": "int",
  "total_mtm_inr": "float"
}
```

---

## 7. DAILY_PNL
**Writer:** Dhan Paper Trade Engine, Performance Monitor
**Readers:** Risk Veto Authority (circuit breaker check), Central Command
**TTL:** Resets each session

```json
{
  "date": "YYYY-MM-DD",
  "realized_pnl_inr": "float",
  "unrealized_pnl_inr": "float",
  "total_pnl_inr": "float",
  "total_pnl_pct": "float",
  "charges_inr": "float",
  "trades_count": "int",
  "wins": "int",
  "losses": "int",
  "win_rate_pct": "float",
  "risk_budget_used_pct": "float",
  "updated_at": "ISO8601 IST"
}
```

---

## 8. KILL_SWITCH
**Writer:** Performance Monitor (auto), Central Command (manual reset)
**Readers:** Risk Veto (first check), all execution agents
**TTL:** Manual reset required

```json
{
  "active": "bool",
  "reason": "DAILY_LOSS_LIMIT | VIX_SPIKE | DHAN_API_FAILURE | CIRCUIT_BREAKER | MANUAL_HALT | null",
  "activated_by": "string | null",
  "activated_at": "ISO8601 IST | null",
  "reset_by": "string | null",
  "reset_at": "ISO8601 IST | null"
}
```
