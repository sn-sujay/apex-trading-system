---
slug: nse-strategy-monthly-walk-forward-validation
title: NSE Strategy — Monthly Walk-Forward Validation
steps:
- description: Fetch latest 30 days of NSE market data (NIFTY, BANKNIFTY, FINNIFTY)
    and read current strategy configurations from Upstash Redis DB1 (STRATEGY_LIBRARY,
    PAPER_STATS, EXECUTION_LOG)
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'Read Upstash Redis DB1 keys: STRATEGY_LIBRARY, PAPER_STATS, EXECUTION_LOG.
    Fetch NSE historical OHLCV data for NIFTY 50, BANKNIFTY, FINNIFTY for the past 30 calendar
    days via Dhan API or web. Output structured dict with: strategies (list with name,
    params), market_data (symbol -> OHLCV list), paper_stats (trades list with entry/exit/pnl)'
- description: Run walk-forward validation on each active strategy — compute Sharpe,
    Calmar, Sortino, max drawdown, win rate, profit factor with real NSE charges (brokerage
    0.03%, STT 0.1%, stamp duty 0.015%)
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'For each strategy in $prev.strategies, run walk-forward backtest
    on $prev.market_data applying $prev.paper_stats slippage baseline. Apply charges:
    brokerage 0.03%, STT 0.1% on sell side, stamp duty 0.015%. Compute per-strategy:
    sharpe_ratio, calmar_ratio, sortino_ratio, max_drawdown_pct, win_rate_pct, profit_factor,
    total_trades. Apply hard gates: REJECT if sharpe < 1.0 OR max_drawdown > 15%.
    Output: validation_results (list), passed (list), rejected (list), overall_grade
    (A/B/C/D)'
- description: Recalibrate strategy confidence grades, produce the full validation report,
    and write WALK_FORWARD_RESULTS, STRATEGY_VALIDATION_REPORT, and STRATEGY_CONFIDENCE_GRADES
    directly to Upstash Redis DB2 (TTL 604800s)
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'Using $prev.validation_results, assign confidence grades: A (sharpe>2.0,
    dd<8%), B (sharpe>1.5, dd<12%), C (sharpe>1.0, dd<15%), D (below gates — flag
    for review). Produce: report_text (full narrative markdown), grades (dict strategy->grade,
    e.g. {S1: A, S2: D}), summary_line (one-sentence overall verdict). Write to Upstash
    Redis DB2 via POST https://{UPSTASH_REDIS_REST_URL_DB2}/pipeline with body
    [["SET","WALK_FORWARD_RESULTS","<pipe-string>","EX",604800],
    ["SET","STRATEGY_VALIDATION_REPORT","<report_text>","EX",604800],
    ["SET","STRATEGY_CONFIDENCE_GRADES","<S1:A|S2:B|S3:D>","EX",604800]].
    WALK_FORWARD_RESULTS format: timestamp:<ISO>|overall_grade:<val>|passed:<count>|rejected:<count>|strategy_grades:<S1:A|S2:D|...>|sharpe_best:<strategy>:<val>|mdd_worst:<strategy>:<val>|summary_line:<text>.
    NEVER call manage_memories.'
- description: Send validation report email to sujaysn6@gmail.com with full results,
    grades, and decay alerts
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'Send email to sujaysn6@gmail.com with subject: APEX NSE Validation
    Report - [MM-YYYY]. Email body: $prev.report_text, grades summary table, summary_line.'
---
