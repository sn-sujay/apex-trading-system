---
slug: apex-15-min-regime-signal-loop
title: APEX — 15-Min Regime + Signal Loop
steps:
- description: Classify current market regime
  agent_slug: india-market-regime-engine
  format_guide: 'Fetch India VIX, PCR, FII/DII flows, NIFTY spot, SGX Nifty, DXY,
    crude oil. Classify regime as TRENDING_UP / TRENDING_DOWN / RANGEBOUND / EVENT
    / HIGH_VOLATILITY / LOW_VOLATILITY. Write MARKET_STATE to APEX_TRADING memory.
    IMPORTANT — manage_memories serialization rule: the value passed to manage_memories
    MUST be a plain JSON object, e.g. {"regime": "TRENDING_UP", "vix": 14.2,
    "nifty_spot": 22150, "confidence": 78, "bias": "bullish", "fii_flow": 320,
    "timestamp": "2026-03-06T08:15:00+05:30"}. Do NOT pass a JSON string
    (json.dumps result), array, or primitive — pass the dict/object directly.
    Output: regime, VIX, NIFTY spot, confidence score.'
- description: Generate new options trade signals based on current regime
  agent_slug: options-strategy-engine
  format_guide: 'Read MARKET_STATE from APEX_TRADING memory (). Based on the
    current regime, generate 1-3 options trade signals for NIFTY or BANKNIFTY. Each
    signal must include: signal_id, strategy (e.g. LONG_PUT_SPREAD, IRON_CONDOR, BULL_CALL_SPREAD),
    underlying, expiry, legs (buy/sell strike+type+LTP), net_debit/credit, max_loss,
    max_profit, SL, target, confidence (0-100), regime tag. Write all signals to APEX_TRADING
    memory under TRADE_SIGNAL_N keys. Memory serialization rule: each value must be
    a plain JSON object (not a JSON string). Only generate signals if regime warrants it
    — skip if RANGEBOUND with low conviction.'
- description: Risk veto — filter and approve signals
  agent_slug: trading-risk-veto-authority
  format_guide: 'Read all new TRADE_SIGNALS and PAPER_STATS from APEX_TRADING memory
    (). Apply: 2% daily loss circuit breaker, 0.5% per-trade risk limit, max
    3 concurrent positions, Kelly Criterion half-Kelly sizing. APPROVE or REJECT each
    signal with reason. Write VETO_REPORT and update APPROVED_SIGNALS in memory.
    Memory serialization rule: all values written to memory must be plain JSON objects,
    not strings. Output: approved signals, rejected signals with reasons, current risk exposure.'
- description: Execute approved signals via Dhan paper trade engine
  agent_slug: dhan-paper-trade-engine
  format_guide: 'Read APPROVED_SIGNALS from APEX_TRADING memory (). For each
    new approved signal not yet in PAPER_LEDGER: fetch live quote from Dhan API, simulate
    fill at mid-price, write EXECUTION_RECORD to memory, update PAPER_LEDGER. Then
    check all open positions for SL/target hits. Write updated PAPER_LEDGER and PAPER_STATS
    to memory. Memory serialization rule: all values written to memory must be plain
    JSON objects (not strings or arrays). Output: new fills, open positions, current MTM P&L.'
- description: 'Post cycle update to #apex-live-trading channel and refresh dashboard'
  agent_slug: nebula
  format_guide: 'Read PAPER_LEDGER, PAPER_STATS, MARKET_STATE, GLOBAL_SENTIMENT_COMPOSITE
    from APEX_TRADING memory. Post a concise update to Nebula channel apex-live-trading using channel_id thrd_069aa5f60dcd7c0580006addd4eab20d:

    APEX CYCLE UPDATE — {time} IST
    REGIME: {regime} | MACRO: {score} {label}
    OPEN POSITIONS:
    - {pos_id}: {instrument} | Spread: {spread} | MTM: {pnl} | SL: {sl} | TGT: {target}
    TOTAL P&L: Realized {realized} + Unrealized {unrealized} = {total}
    NEW FILLS: {fills_this_cycle}
    ALERTS: {alerts}'
---

Runs every 15 minutes during NSE market hours. Regime engine classifies market state,
options engine generates signals, risk veto filters, and paper trade engine executes.
