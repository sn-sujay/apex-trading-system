---
slug: apex-15-min-email-monitor
title: APEX 15-Min Email Monitor
steps:
- description: Read APEX state from memory and send live update email
  agent_slug: apex-trading-monitor
  format_guide: 'Read MARKET_REGIME, PAPER_LEDGER, APPROVED_SIGNALS from memory. Get
    current IST time. Send email to sujaysn6@gmail.com. Subject: APEX LIVE [HH:MM
    IST] | [REGIME] | P&L [+/-Rs X]. Body: market snapshot (NIFTY, BANKNIFTY, VIX,
    PCR, Crude, DXY), regime details, open positions table (symbol, entry, LTP, MTM
    P&L, SL dist, target dist, status), alerts (approaching targets, SL risks, expiry
    warnings), daily P&L summary (realized + unrealized + total, win rate, daily DD%),
    next scan time. Use URGENT prefix if VIX > 25, position at SL risk, or daily loss
    > Rs 5000.'
---

Every 15 minutes during NSE market hours, reads live APEX trading state from memory and sends a formatted email update to sujaysn6@gmail.com.
