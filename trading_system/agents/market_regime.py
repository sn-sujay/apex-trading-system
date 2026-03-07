"""
APEX Agent 7: MarketRegimeAgent
Classifies current market regime: Bull/Bear/Sideways/HighVol/Crisis.
Used by MasterDecisionMaker to weight/filter signals from all other agents.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, MarketRegime, SignalTimeframe, AssetClass
from ..core.constants import VOLATILITY_KILL_SWITCH_VIX


class MarketRegimeAgent(APEXBaseAgent):
    """
    Regime detection using:
    - India VIX level and trend
    - Nifty 200-day SMA position
    - 20-day historical volatility
    - Trend strength (ADX)
    - Breadth (% stocks above 50-DMA approximation)
    """

    def __init__(self, config=None):
        super().__init__("MarketRegimeAgent", "1.0.0", config)
        self._current_regime: MarketRegime = MarketRegime.SIDEWAYS

    async def _fetch_data(self) -> Dict[str, Any]:
        import yfinance as yf
        data = {}
        symbols = {"nifty": "^NSEI", "vix": "^INDIAVIX", "us_vix": "^VIX"}
        for key, sym in symbols.items():
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                data[key] = df
            except Exception as e:
                self.logger.warning(f"Regime data fetch failed for {sym}: {e}")
        return data

    def _detect_regime(self, nifty_df, vix_df) -> Tuple[MarketRegime, float, str]:
        if nifty_df is None or nifty_df.empty:
            return MarketRegime.SIDEWAYS, 0.4, "Insufficient data"

        close = nifty_df["Close"] if "Close" in nifty_df.columns else nifty_df["close"]

        # SMA200 position
        sma200 = close.rolling(200).mean()
        above_sma200 = float(close.to_numpy()[-1]) > float(sma200.to_numpy()[-1]) if not sma200.empty else True

        # 20-day realized volatility (annualized)
        returns = close.pct_change().dropna()
        vol_20d = float(returns.to_numpy()[-20:].std() * np.sqrt(252) * 100) if len(returns) >= 20 else 15.0

        # 60-day trend return
        trend_return = float((close.to_numpy()[-1] / close.to_numpy()[-61] - 1) * 100) if len(close) > 61 else 0.0

        # VIX
        india_vix = 15.0
        if vix_df is not None and not vix_df.empty:
            vc = vix_df["Close"] if "Close" in vix_df.columns else vix_df["close"]
            india_vix = float(vc.to_numpy()[-1])

        # Regime classification
        factors = []
        if india_vix >= VOLATILITY_KILL_SWITCH_VIX:
            regime = MarketRegime.CRISIS
            confidence = 0.90
            factors.append(f"India VIX={india_vix:.1f} CRISIS level (>={VOLATILITY_KILL_SWITCH_VIX})")
        elif vol_20d > 25:
            regime = MarketRegime.HIGH_VOL
            confidence = 0.80
            factors.append(f"Realized vol={vol_20d:.1f}% (high volatility)")
        elif trend_return > 8 and above_sma200 and vol_20d < 18:
            regime = MarketRegime.BULL_TREND
            confidence = 0.85
            factors.append(f"60d return=+{trend_return:.1f}%, above SMA200, low vol")
        elif trend_return < -8 and not above_sma200:
            regime = MarketRegime.BEAR_TREND
            confidence = 0.85
            factors.append(f"60d return={trend_return:.1f}%, below SMA200")
        elif vol_20d < 10:
            regime = MarketRegime.LOW_VOL
            confidence = 0.70
            factors.append(f"Realized vol={vol_20d:.1f}% (suppressed volatility)")
        else:
            regime = MarketRegime.SIDEWAYS
            confidence = 0.60
            factors.append(f"60d return={trend_return:.1f}%, indecisive")

        self._current_regime = regime
        reasoning = f"Regime={regime.value}. VIX={india_vix:.1f}, Vol20d={vol_20d:.1f}%, Trend60d={trend_return:.1f}%. " + "; ".join(factors)
        return regime, confidence, reasoning

    async def analyze(self) -> AgentSignal:
        data = await self._fetch_data()
        regime, confidence, reasoning = self._detect_regime(
            data.get("nifty"), data.get("vix")
        )

        # Regime maps to direction
        regime_direction_map = {
            MarketRegime.BULL_TREND: SignalDirection.BUY,
            MarketRegime.BEAR_TREND: SignalDirection.SELL,
            MarketRegime.SIDEWAYS: SignalDirection.NEUTRAL,
            MarketRegime.HIGH_VOL: SignalDirection.NEUTRAL,
            MarketRegime.LOW_VOL: SignalDirection.BUY,
            MarketRegime.CRISIS: SignalDirection.STRONG_SELL,
        }
        direction = regime_direction_map[regime]

        india_vix = None
        if data.get("vix") is not None and not data["vix"].empty:
            vc = data["vix"]["Close"] if "Close" in data["vix"].columns else data["vix"]["close"]
            india_vix = float(vc.to_numpy()[-1])

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            symbol="NIFTY 50",
            reasoning=reasoning,
            key_factors=[f"Current Regime: {regime.value}"],
            regime=regime,
            india_vix=india_vix,
            timeframe=SignalTimeframe.POSITIONAL,
            asset_class=AssetClass.INDEX,
            supporting_data={"regime": regime.value, "india_vix": india_vix},
        )

    @property
    def current_regime(self) -> MarketRegime:
        return self._current_regime
