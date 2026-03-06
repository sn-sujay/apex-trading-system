# APEX Agent Registry

All agents run inside Nebula. Slugs are used for delegation.

| Agent Name | Slug | Primary Role |
|---|---|---|
| India Trading Central Command | india-trading-central-command | Orchestration hub |
| India Market Regime Engine | india-market-regime-engine | Regime classification |
| Sentiment Intelligence Engine | sentiment-intelligence-engine | News + social NLP |
| NSE Option Chain Monitor | nse-option-chain-monitor | PCR/GEX/IV signals |
| Options Strategy Engine | options-strategy-engine | Signal generation |
| APEX Validator Gate | apex-validator-gate | Pre-execution quality gate |
| APEX Validator | apex-validator | Data quality validation |
| Trading Risk Veto Authority | trading-risk-veto-authority | 6-gate risk filter |
| Dhan Paper Trade Engine | dhan-paper-trade-engine | Paper execution + MTM |
| Dhan Live Order Executor | dhan-live-order-executor | Live execution (future) |
| Live Trade Performance Monitor | live-trade-performance-monitor | Sharpe/decay detection |
| APEX Self-Evolution Engine | apex-self-evolution-engine | Post-session learning |
| APEX System Health Monitor | apex-system-health-monitor | Watchdog + alerting |
| APEX Error Monitor | apex-error-monitor | Error detection + routing |
| APEX Fix Verifier | apex-fix-verifier | Fix verification |
| Tony Autonomous Senior Dev | tony-autonomous-senior-dev | Code review + self-healing |
| Global Macro Intelligence Scanner | global-macro-intelligence-scanner | Overnight macro scan |
| NSE Strategy Validation Engine | nse-strategy-validation-engine | Backtesting |
| APEX Trading Monitor | apex-trading-monitor | On-demand status emails |
