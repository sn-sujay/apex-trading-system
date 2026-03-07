"""APEX Trading Intelligence System — Global Constants"""

# ── Indian Market Sessions ──────────────────────────────────────────────────
NSE_OPEN_TIME = "09:15"
NSE_CLOSE_TIME = "15:30"
NSE_PRE_OPEN_START = "09:00"
NSE_PRE_OPEN_END = "09:08"
NSE_MUHURAT_TRADING = False  # toggle on Diwali

# ── Exchange Calendars ──────────────────────────────────────────────────────
NSE_EXCHANGE = "NSE"
BSE_EXCHANGE = "BSE"
MCX_EXCHANGE = "MCX"
SGX_NIFTY_EXCHANGE = "SGX"

# ── Asset Class Codes ───────────────────────────────────────────────────────
NIFTY50_SYMBOL = "NIFTY 50"
BANKNIFTY_SYMBOL = "NIFTY BANK"
SENSEX_SYMBOL = "SENSEX"
NIFTY_FUT_PREFIX = "NIFTY"
BANKNIFTY_FUT_PREFIX = "BANKNIFTY"

# ── Global Indices ──────────────────────────────────────────────────────────
SP500_SYMBOL = "^GSPC"
NASDAQ_SYMBOL = "^IXIC"
DOW_SYMBOL = "^DJI"
FTSE_SYMBOL = "^FTSE"
NIKKEI_SYMBOL = "^N225"
HANGSENG_SYMBOL = "^HSI"
DAX_SYMBOL = "^GDAXI"
SGX_NIFTY_SYMBOL = "SGXNIFTY"

# ── Commodities ─────────────────────────────────────────────────────────────
GOLD_MCX_SYMBOL = "GOLD"
SILVER_MCX_SYMBOL = "SILVER"
CRUDEOIL_MCX_SYMBOL = "CRUDEOIL"
NATURALGAS_MCX_SYMBOL = "NATURALGAS"
GOLD_FUTURES_SYMBOL = "GC=F"
CRUDE_FUTURES_SYMBOL = "CL=F"

# ── Forex ───────────────────────────────────────────────────────────────────
USDINR_SYMBOL = "USDINR=X"
EURINR_SYMBOL = "EURINR=X"
DXY_SYMBOL = "DX-Y.NYB"

# ── Signal Thresholds ───────────────────────────────────────────────────────
STRONG_SIGNAL_THRESHOLD = 0.75
WEAK_SIGNAL_THRESHOLD = 0.40
CONSENSUS_QUORUM = 0.60          # 60% of agents must agree
CONFLICT_THRESHOLD = 0.30        # conflict if bull/bear split within 30%

# ── Agent Weights (sum to 1.0) ──────────────────────────────────────────────
AGENT_WEIGHTS = {
    "IndianMarketDataAgent": 0.08,
    "GlobalMarketDataAgent": 0.07,
    "CommoditiesAgent": 0.05,
    "TechnicalAnalysisAgent": 0.10,
    "AlgoStrategyAgent": 0.08,
    "OptionsDerivativesAgent": 0.07,
    "MarketRegimeAgent": 0.06,
    "SGXPreMarketAgent": 0.04,
    "FundamentalAnalysisAgent": 0.06,
    "FIIDIIFlowAgent": 0.06,
    "RBIIndianMacroAgent": 0.05,
    "GlobalMacroAgent": 0.05,
    "IndianNewsEventsAgent": 0.04,
    "GlobalNewsAgent": 0.04,
    "SentimentPositioningAgent": 0.05,
    "ZeroDTEExpiryAgent": 0.05,
    "RiskManagementAgent": 0.05,  # veto power
    "PortfolioManagementAgent": 0.05,
}

# ── Risk Parameters ─────────────────────────────────────────────────────────
MAX_POSITION_SIZE_PCT = 0.05     # 5% of portfolio per trade
MAX_DAILY_LOSS_PCT = 0.02        # 2% max daily drawdown → kill switch
MAX_OPEN_POSITIONS = 10
DEFAULT_STOP_LOSS_PCT = 0.015    # 1.5%
DEFAULT_TARGET_PCT = 0.03        # 3% (2:1 RR)
VOLATILITY_KILL_SWITCH_VIX = 30  # India VIX threshold

# ── Kafka Topics ────────────────────────────────────────────────────────────
KAFKA_TICK_TOPIC = "apex.ticks"
KAFKA_SIGNAL_TOPIC = "apex.signals"
KAFKA_DECISION_TOPIC = "apex.decisions"
KAFKA_ORDER_TOPIC = "apex.orders"
KAFKA_RISK_TOPIC = "apex.risk"

# ── Redis Keys ──────────────────────────────────────────────────────────────
REDIS_SIGNAL_PREFIX = "apex:signal:"
REDIS_PRICE_PREFIX = "apex:price:"
REDIS_REGIME_KEY = "apex:regime:current"
REDIS_POSITIONS_KEY = "apex:positions"
REDIS_PNL_KEY = "apex:pnl:daily"

# ── Timeframes ──────────────────────────────────────────────────────────────
TIMEFRAME_1M = "1minute"
TIMEFRAME_3M = "3minute"
TIMEFRAME_5M = "5minute"
TIMEFRAME_15M = "15minute"
TIMEFRAME_30M = "30minute"
TIMEFRAME_1H = "60minute"
TIMEFRAME_1D = "day"
TIMEFRAME_1W = "week"

# ── Model Paths ─────────────────────────────────────────────────────────────
REGIME_MODEL_PATH = "models/regime_classifier.pkl"
SENTIMENT_MODEL_PATH = "models/sentiment_bert.pkl"
SIGNAL_MODEL_PATH = "models/signal_ensemble.pkl"

# -- Test Compatibility Aliases --
NIFTY = NIFTY50_SYMBOL
NIFTY_50 = NIFTY50_SYMBOL
BANKNIFTY = BANKNIFTY_SYMBOL
NSE = NSE_EXCHANGE
BSE = BSE_EXCHANGE
