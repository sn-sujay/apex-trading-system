---
slug: apex-15-min-live-update-to-channel
title: APEX — 15-Min Live Update to Channel
steps:
- description: Cycle 1 of 4 — Regime + Signal + Veto + Positions + Post (immediate)
  agent_id: agt_069a8dd420077c9f800044f12cee1a70
  agent_slug: india-market-regime-engine
  format_guide: Read APEX_TRADING memory for GLOBAL_SENTIMENT_COMPOSITE. Classify
    regime as TRENDING_UP/TRENDING_DOWN/RANGE_BOUND/HIGH_VOLATILITY with confidence
    0-100. Write MARKET_REGIME to memory with label, confidence, vix_band, fii_flow,
    bias, timestamp. Output regime summary.
- description: Generate signals for Cycle 1
  agent_id: agt_069a8e06e26174ff8000d093fd178c74
  agent_slug: options-strategy-engine
  format_guide: Read MARKET_REGIME from memory. Generate 1-3 NIFTY/BANKNIFTY options
    signals with symbol, strategy, strikes, expiry, entry_price, stop_loss, target,
    confidence, rationale. Write TRADE_SIGNALS to memory.
- description: Risk veto for Cycle 1
  agent_id: agt_069a8e2044a37c2e80006158e3af8bd6
  agent_slug: trading-risk-veto-authority
  format_guide: Read TRADE_SIGNALS and PAPER_LEDGER from memory. Apply 2% daily loss
    circuit breaker, 0.5% per-trade risk, max 3 positions, Kelly sizing. APPROVE or
    VETO each signal. Write APPROVED_SIGNALS to memory.
- description: Paper trade execution + SL/target monitor for Cycle 1
  agent_id: agt_069a8fd4c57a733e8000f75cd903213b
  agent_slug: dhan-paper-trade-engine
  format_guide: Read PAPER_LEDGER open positions. Fetch live LTP via Dhan API. Check
    SL/target hits, close triggered positions. Execute APPROVED_SIGNALS as new paper
    trades. Update PAPER_LEDGER with MTM P&L. Output position status table.
- description: 'Post Cycle 1 live update to #apex-live-trading channel'
  agent_slug: nebula
  format_guide: 'Read MARKET_REGIME, APPROVED_SIGNALS, PAPER_LEDGER from memory. Get
    current IST time (UTC+5:30). Compose this exact format and post it using send_channel_message
    with channel_id=''thrd_069aa5f60dcd7c0580006addd4eab20d'' (do NOT use channel
    name, always use this channel_id directly):


    **APEX LIVE — [HH:MM IST]**

    **REGIME:** [label] | Conf: [X]% | Bias: [bias] | VIX: [band]

    **MACRO:** Score [score] [label] | Crude: [price] | DXY: [level]

    **SIGNALS:** [APPROVED/VETOED] [symbol] [strategy] — Entry:[price] SL:[price]
    Tgt:[price] Conf:[X]%

    **POSITIONS:**

    | Symbol | Entry | LTP | MTM | SL dist | Tgt dist | DTE |

    **P&L:** Total:[amt] | Realized:[amt] | Unrealized:[amt] | WinRate:[X]% | DailyDD:[X]%


    CRITICAL: call send_channel_message(channel_id=''thrd_069aa5f60dcd7c0580006addd4eab20d'',
    message=''...'', delivery_mode=''message''). Never use channel name string.'
- description: Wait 15 minutes then run Cycle 2 — Regime + Signal + Veto + Positions
    + Post
  agent_id: agt_069a8dd420077c9f800044f12cee1a70
  agent_slug: india-market-regime-engine
  format_guide: 'Sleep/wait 15 minutes (900 seconds). Then re-run regime classification:
    read GLOBAL_SENTIMENT_COMPOSITE from memory, fetch fresh India VIX and PCR data,
    reclassify regime. Write updated MARKET_REGIME to memory. Then generate new signals
    (options-strategy-engine logic), run risk veto (trading-risk-veto-authority logic),
    update paper positions (dhan-paper-trade-engine logic), and post updated live
    update to #apex-live-trading channel in same format as Cycle 1 with updated timestamp.
    Repeat this full pipeline including the channel post.'
- description: Wait 15 minutes then run Cycle 3 — Regime + Signal + Veto + Positions
    + Post
  agent_id: agt_069a8dd420077c9f800044f12cee1a70
  agent_slug: india-market-regime-engine
  format_guide: 'Sleep/wait 15 minutes (900 seconds) after Cycle 2 completes. Re-run
    full pipeline: regime classification, signal generation, risk veto, paper position
    monitoring, and post updated live update to #apex-live-trading channel with current
    timestamp. Same format as previous cycles.'
- description: Wait 15 minutes then run Cycle 4 — Regime + Signal + Veto + Positions
    + Post
  agent_id: agt_069a8dd420077c9f800044f12cee1a70
  agent_slug: india-market-regime-engine
  format_guide: 'Sleep/wait 15 minutes (900 seconds) after Cycle 3 completes. Re-run
    full pipeline: regime classification, signal generation, risk veto, paper position
    monitoring, and post final update to #apex-live-trading channel with current timestamp.
    This is the 4th and final cycle of this hourly run.'
---

Runs every 15 minutes during NSE market hours (09:15-15:30 IST) via cron schedule */15 9-15 * * 1-5. Posts live regime, signals, positions, and P&L updates to #apex-live-trading channel.
