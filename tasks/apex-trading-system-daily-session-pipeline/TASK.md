---
slug: apex-trading-system-daily-session-pipeline
title: APEX Trading System — Daily Session Pipeline
steps:
- description: Classify current market regime using latest VIX, PCR, FII/DII flows,
    option chain data, and global macro sentiment from memory
  agent_slug: india-market-regime-engine
  format_guide: Read GLOBAL_SENTIMENT, GLOBAL_SENTIMENT_ASIA, VIX data. Classify regime
    as TRENDING_UP/DOWN, RANGING, BREAKOUT, EVENT, or CHOPPY with confidence 0-100.
    Save to MARKET_REGIME in memory.
- description: Generate trade signals for the next session based on current regime,
    option chain OI data, and global macro context
  agent_slug: options-strategy-engine
  format_guide: Read MARKET_REGIME from memory. Evaluate all 6 strategy types. Generate
    TRADE_SIGNALs with grade A/B/C, confidence, entry conditions, SL/target levels.
    Save to TRADE_SIGNAL and APPROVED_SIGNALS in memory.
- description: 'Review all generated trade signals against risk rules: Kelly position
    sizing, daily loss limits, consecutive loss cooling, max concurrent positions'
  agent_slug: trading-risk-veto-authority
  format_guide: Read TRADE_SIGNALs from memory. Apply all 5 risk gates. Approve, conditionally
    approve, or reject each signal. Save VETO_REPORT to memory.
- description: Execute approved signals in paper mode, monitor open positions for
    SL/target hits, update ledger with latest MTM P&L
  agent_slug: dhan-paper-trade-engine
  format_guide: Read APPROVED_SIGNALS and PAPER_LEDGER from memory. Simulate fills
    at mid-price. Check SL/target levels for all open positions. Update PAPER_LEDGER
    and EXECUTION_LOG in memory with current P&L.
- description: 'Run full post-session evolution cycle: trade attribution, decay detection,
    calibration, regime accuracy, risk parameter updates, pattern discovery, and agent
    corrections'
  agent_slug: apex-self-evolution-engine
  format_guide: Read all EXECUTION_LOGs, VETO_REPORTs, PAPER_STATS from memory. Run
    all 7 analysis modules. Save EVOLUTION_LOG, STRATEGY_UPDATES, CALIBRATION to memory.
    Send evolution report email to sujaysn6@gmail.com.
- description: 'Send end-of-day status email summarizing the full session: regime,
    all positions closed/open, daily P&L, evolution changes applied, and next session
    preview'
  agent_slug: apex-trading-monitor
  format_guide: 'Read PAPER_LEDGER, PAPER_STATS, MARKET_REGIME, EVOLUTION_LOG from
    memory. Send richly formatted EOD status email to sujaysn6@gmail.com with subject:
    APEX EOD [DATE] | P&L [+/-Rs X] | [REGIME] | Health: [STATUS].'
---

Master daily coordination pipeline for the APEX Intraday Trading System. Runs the complete end-of-day evolution and learning cycle after NSE close.
