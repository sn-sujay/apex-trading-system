---
slug: apex-forex-intraday-signal-pipeline
title: APEX Forex — Intraday Signal Pipeline
steps:
- description: 'Run Forex Macro Regime Engine: scrape DXY, US10Y, crude oil, FII/FPI
    flows, classify INR regime as BULLISH_INR/BEARISH_INR/RANGING/RBI_INTERVENTION_RISK,
    set FOREX_BLACKOUT flag for event windows. Output ONLY two plain pipe-delimited
    strings — do NOT call manage_memories yourself.'
  agent_id: agt_069ad4f19cdc74b78000997db63737fe
  agent_slug: apex-forex-macro-regime-engine
  action_key: scrape-page
  action_props:
    url: https://www.nseindia.com/market-data/currency-derivatives
  format_guide: 'Output two labelled blocks: REGIME_STRING: regime:<value>|confidence:<0-100>|dxy:<val>|dxy_change_pct:<val>|us10y:<val>|crude_brent:<val>|crude_change_pct:<val>|fii_net_flow_cr:<val>|rbi_intervention_signal:<val>|timestamp:<ISO>|next_blackout_event:<val>  and  BLACKOUT_STRING:
    blackout:<true/false>|reason:<text or NONE>'
- description: Write FOREX_MARKET_REGIME and FOREX_BLACKOUT to memory from previous
    step output
  agent_slug: nebula
  format_guide: 'Read REGIME_STRING and BLACKOUT_STRING from $prev output. Call manage_memories
    twice: (1) key=FOREX_MARKET_REGIME, value=REGIME_STRING value, category=user_preference,
    scope=global. (2) key=FOREX_BLACKOUT, value=BLACKOUT_STRING value, category=user_preference,
    scope=global. Values must be plain strings. Output memory_write_status.'
- description: 'Run INR Currency Signal Engine: read FOREX_MARKET_REGIME and FOREX_BLACKOUT
    from memory. Skip if blackout active. Fetch live NSE currency futures prices.
    Run 4 strategy modules (Breakout+Momentum, Mean Reversion, MTF EMA Trend, Macro
    Carry) for USD/INR, EUR/INR, GBP/INR, JPY/INR. Output ONLY a pipe-delimited SIGNALS_STRING
    — do NOT call manage_memories yourself.'
  agent_id: agt_069ad501de0e71f180004e91a2e07313
  agent_slug: inr-currency-signal-engine
  format_guide: 'Output SIGNALS_STRING: generated_at:<ISO>|regime:<val>|blackout:<bool>|signals:<signal_id>:<pair>:<direction>:<entry>:<sl>:<tp>:<strategy>:<confidence>:<lot_size>;<next_signal...>|skipped_reason:<text
    or NONE>'
- description: Write FOREX_SIGNALS to memory from previous step output
  agent_slug: nebula
  format_guide: 'Read SIGNALS_STRING from $prev output. Call manage_memories: key=FOREX_SIGNALS,
    value=SIGNALS_STRING, category=user_preference, scope=global. Value must be a
    plain string. Output memory_write_status.'
- description: 'Run Forex Risk Veto Authority: read FOREX_SIGNALS, FOREX_PAPER_LEDGER,
    FOREX_BLACKOUT from memory. Apply all 7 hard rules. Output APPROVED_SIGNALS_STRING
    and VETO_LOG_STRING — do NOT call manage_memories yourself.'
  agent_id: agt_069ad50e9d64797b80008d05eb78c78f
  agent_slug: forex-risk-veto-authority
  format_guide: 'Output APPROVED_SIGNALS_STRING: approved signals pipe-delimited,
    same format as SIGNALS_STRING but only approved ones. Output VETO_LOG_STRING:
    timestamp:<ISO>|vetoed:<count>|approved:<count>|entries:<signal_id>:<reason_code>:<rule_number>;<next...>'
- description: Write APPROVED_FOREX_SIGNALS and FOREX_VETO_REPORT to memory
  agent_slug: nebula
  format_guide: 'Read APPROVED_SIGNALS_STRING and VETO_LOG_STRING from $prev. Call
    manage_memories twice: (1) key=APPROVED_FOREX_SIGNALS, value=APPROVED_SIGNALS_STRING,
    category=user_preference, scope=global. (2) key=FOREX_VETO_REPORT, value=VETO_LOG_STRING,
    category=user_preference, scope=global. Plain strings only. Output memory_write_status.'
- description: 'Run Dhan Forex Paper Engine: read APPROVED_FOREX_SIGNALS from memory.
    Fetch live NSE currency prices. Simulate fills with realistic slippage. Mark-to-market
    open positions. Auto-close on SL/TP. Auto-square-off at 16:55 IST. Output LEDGER_STRING
    — do NOT call manage_memories yourself.'
  agent_id: agt_069ad50e94517ff48000d30ecbaa736e
  agent_slug: dhan-forex-paper-engine
  format_guide: 'Output LEDGER_STRING: capital:<val>|available_margin:<val>|blocked_margin:<val>|realized_pnl:<val>|unrealized_pnl:<val>|today_realized_pnl:<val>|total_trades:<val>|win_count:<val>|loss_count:<val>|open_positions:<pair>:<direction>:<entry>:<qty>:<mtm>;<next...>|closed_trades:<trade_id>:<pair>:<pnl>;<next...>'
- description: Write FOREX_PAPER_LEDGER to memory
  agent_slug: nebula
  format_guide: 'Read LEDGER_STRING from $prev. Call manage_memories: key=FOREX_PAPER_LEDGER,
    value=LEDGER_STRING, category=user_preference, scope=global. Plain string only.
    Output memory_write_status.'
---
