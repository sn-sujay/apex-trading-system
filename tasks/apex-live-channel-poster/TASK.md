---
slug: apex-live-channel-poster
title: APEX Live Channel Poster
steps:
- description: Read APEX live update from memory and post it in this channel
  agent_slug: nebula
  format_guide: 'Read MARKET_REGIME, PAPER_LEDGER, APPROVED_SIGNALS from memory. Post
    a complete live update here with: timestamp IST, regime, NIFTY/BANKNIFTY prices,
    VIX, PCR, open positions table, P&L summary, alerts.'
---

Reads APEX live update from memory and posts it in the apex-live-trading channel every 15 min.
