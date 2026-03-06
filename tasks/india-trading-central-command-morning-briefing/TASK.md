---
slug: india-trading-central-command-morning-briefing
title: India Trading Central Command — Morning Briefing
steps:
- description: Run India Market Regime Engine to get current MARKET_STATE
  agent_slug: india-market-regime-engine
  format_guide: Output structured MARKET_STATE JSON with regime classification, VIX,
    PCR, FII/DII flows, and key levels
- description: Run Sentiment Intelligence Engine to get current SENTIMENT_SCORE
  agent_slug: sentiment-intelligence-engine
  format_guide: Output SENTIMENT_SCORE (-1.0 to +1.0) with top bullish/bearish signals
    from Economic Times, MoneyControl, and Twitter/X
- description: Synthesize morning briefing and send email to sujaysn6@gmail.com with
    regime, sentiment, recommended strategies, and risk parameters for the day
  agent_slug: india-trading-central-command
  format_guide: 'Email subject: ''APEX Morning Briefing — [DATE] | Regime: [REGIME]''.
    Body: regime classification, sentiment score, top 2-3 strategy recommendations
    from Options Strategy Engine, daily risk budget (2% max loss), key levels to watch,
    and any global macro alerts. Use $step.1 for MARKET_STATE and $step.2 for SENTIMENT_SCORE.'
---

Pre-market orchestration at 09:00 IST every trading day. Delegates to Market Regime Engine and Sentiment Engine to collect MARKET_STATE and SENTIMENT_SCORE, then synthesizes a morning briefing with regime classification, recommended strategies, and daily risk parameters. Sends digest email to sujaysn6@gmail.com.
