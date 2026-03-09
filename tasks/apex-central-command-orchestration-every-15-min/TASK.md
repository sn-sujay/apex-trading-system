---
slug: apex-central-command-orchestration-every-15-min
title: APEX — Central Command Orchestration (Every 15 Min)
steps:
- description: Read MARKET_REGIME, SENTIMENT_SNAPSHOT, OPTION_CHAIN_SNAPSHOT from Upstash
    Redis DB1. Check SIGNAL_BLOCKED flag. If SIGNAL_BLOCKED is true, log blocked state
    and stop. If not blocked, delegate to options-strategy-engine to generate trade signals
    based on current regime, sentiment, and option chain data. Write TRADE_SIGNALS directly
    to Upstash Redis DB1 (TTL 900s).
  agent_id: agt_069a8db67d5779148000bbc9e5901e1a
  agent_slug: india-trading-central-command
- description: Validate all upstream data quality. Read MARKET_REGIME, SENTIMENT_SNAPSHOT,
    OPTION_CHAIN_SNAPSHOT, TRADE_SIGNALS from Upstash Redis DB1. Check freshness, confidence,
    and completeness. Write VALIDATION_RESULT and SIGNAL_BLOCKED directly to Upstash Redis
    DB1 (TTL 1200s). Append to VALIDATION_LOG.
  agent_id: agt_069aae33c1347cdc800054a7abcc8a9d
  agent_slug: apex-validator-gate
- description: Run risk veto on validated trade signals. Read TRADE_SIGNALS and VALIDATION_RESULT
    from Upstash Redis DB1. If SIGNAL_BLOCKED is true, skip execution. Apply 2% daily loss
    circuit breaker, 0.5% per-trade risk limit, Kelly position sizing, max 3 concurrent
    positions check. Write VETO_RESULT and APPROVED_SIGNALS directly to Upstash Redis DB1
    (TTL 1200s).
  agent_id: agt_069a8e2044a37c2e80006158e3af8bd6
  agent_slug: trading-risk-veto-authority
- description: Execute approved paper trades. Read VETO_RESULT and APPROVED_SIGNALS from
    Upstash Redis DB1. For each APPROVED signal, simulate fill at mid-price via Dhan API
    live quotes. Update PAPER_LEDGER and EXECUTION_RECORD directly in Upstash Redis DB1
    (PAPER_LEDGER TTL 3600s, EXECUTION_RECORD TTL 3600s). Mark-to-market all open positions.
  agent_id: agt_069a8fd4c57a733e8000f75cd903213b
  agent_slug: dhan-paper-trade-engine
---

Runs every 15 minutes during NSE market hours. Central Command reads all data snapshots
from Upstash Redis DB1, triggers the Validator Gate, then routes to Options Strategy Engine,
Risk Veto, and Paper Trade Engine in a coordinated pipeline. All agents write Redis directly.
