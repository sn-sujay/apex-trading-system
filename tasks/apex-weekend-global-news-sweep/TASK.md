---
slug: apex-weekend-global-news-sweep
title: APEX — Weekend Global News Sweep
steps:
- description: Search for global macro news and geopolitical events from the past
    48 hours relevant to Indian markets
  action_key: web-search
  action_props:
    query: India NSE stock market Fed RBI crude oil DXY geopolitical news this weekend
      macro events 2026
- description: Search for US economic data, earnings, and Fed signals from the weekend
  action_key: web-search
  action_props:
    query: US Federal Reserve economic data jobs report earnings S&P500 weekend news
      impact Asia markets
- description: Search for SGX Nifty, Asian markets, and any India-specific corporate
    or political news
  action_key: web-search
  action_props:
    query: SGX Nifty Nifty50 BankNifty outlook Monday open FII DII flows India corporate
      news weekend
- description: 'Synthesize all three search results into a structured WEEKEND_MACRO_SNAPSHOT.
    Output ONLY a plain pipe-delimited string in this exact format — no JSON objects,
    no nested structures: timestamp:<ISO>|sentiment_bias:<BULLISH/BEARISH/NEUTRAL>|confidence:<0-100>|fed_signal:<HAWKISH/DOVISH/NEUTRAL>|crude_bias:<UP/DOWN/FLAT>|dxy_bias:<UP/DOWN/FLAT>|sgx_nifty_signal:<PREMIUM/DISCOUNT/FLAT>|monday_opening_bias:<GAP_UP/GAP_DOWN/FLAT>|key_events:<comma-separated
    list of up to 10 headlines>|analyst_note:<2-3 sentence plain English summary>.
    Also output a SWEEP_LOG string: timestamp:<ISO>|run:WEEKEND_SWEEP|status:COMPLETE|events_found:<count>.
    Do NOT call manage_memories yourself. Do NOT write to any file.'
  agent_id: agt_069a8f413b5b71f08000659d18ea5ee8
  agent_slug: global-macro-intelligence-scanner
  format_guide: 'Output two clearly labelled blocks: SNAPSHOT_STRING: <the full pipe-delimited
    snapshot string> and SWEEP_LOG_STRING: <the pipe-delimited log string>. Nothing
    else.'
- description: Read SNAPSHOT_STRING and SWEEP_LOG_STRING from the previous step output
    and write both to memory. Use manage_memories with action=save, category=user_preference,
    scope=global. Key WEEKEND_MACRO_SNAPSHOT = the SNAPSHOT_STRING value. Key WEEKEND_SWEEP_LOG
    = the SWEEP_LOG_STRING value. These are plain strings — pass them exactly as-is,
    no JSON wrapping.
  agent_slug: nebula
---
