"""
APEX Agent 2: GlobalMarketDataAgent
Monitors US/EU/Asian markets and measures correlation with Indian markets.
"""
from __future__ import annotations
import asyncio
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass
from ..core.constants import SP500_SYMBOL, NASDAQ_SYMBOL, NIKKEI_SYMBOL, HANGSENG_SYMBOL, DAX_SYMBOL


class GlobalMarketDataAgent(APEXBaseAgent):
    """
    Analyzes global equity indices and their lead/lag effect on Nifty.
    US markets close → Asian markets open → India opens at 9:15 AM IST.
    SGX Nifty provides the most direct signal before India open.
    """

    GLOBAL_SYMBOLS = {
        "SP500":    SP500_SYMBOL,
        "NASDAQ":   NASDAQ_SYMBOL,
        "NIKKEI":   NIKKEI_SYMBOL,
        "HANGSENG": HANGSENG_SYMBOL,
        "DAX":      DAX_SYMBOL,
        "FTSE":     "^FTSE",
        "VIX":      "^VIX",
        "INDIA_VIX":"^INDIAVIX",
    }

    # Historical correlation of each index with Nifty (approximate)
    NIFTY_CORRELATIONS = {
        "SP500":    0.72,
        "NASDAQ":   0.68,
        "NIKKEI":   0.55,
        "HANGSENG": 0.50,
        "DAX":      0.60,
        "FTSE":     0.45,
    }

    def __init__(self, config=None):
        super().__init__("GlobalMarketDataAgent", "1.0.0", config)

    async def _fetch_data(self) -> Dict[str, Any]:
        import yfinance as yf
        results = {}
        for name, symbol in self.GLOBAL_SYMBOLS.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d", interval="1d")
                if not hist.empty:
                    results[name] = {
                        "close": float(hist["Close"].iloc[-1]),
                        "prev_close": float(hist["Close"].iloc[-2]) if len(hist) > 1 else None,
                        "change_pct": float(hist["Close"].pct_change().iloc[-1] * 100),
                        "5d_return": float((hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100),
                    }
            except Exception as e:
                self.logger.warning(f"Failed to fetch {name} ({symbol}): {e}")
        return results

    async def analyze(self) -> AgentSignal:
        data = await self._fetch_data()
        if not data:
            return self._no_signal("No global market data available")

        bullish_score = 0.0
        total_weight = 0.0
        key_factors = []

        for name, corr in self.NIFTY_CORRELATIONS.items():
            if name in data:
                chg = data[name]["change_pct"]
                weighted_contribution = chg * corr / 100
                bullish_score += weighted_contribution
                total_weight += corr
                direction_str = "UP" if chg > 0 else "DOWN"
                key_factors.append(f"{name} {direction_str} {abs(chg):.2f}%")

        india_vix = data.get("INDIA_VIX", {}).get("close", 15.0)
        us_vix = data.get("VIX", {}).get("close", 20.0)

        # VIX penalty
        if india_vix and india_vix > 25:
            bullish_score *= 0.6
            key_factors.append(f"India VIX={india_vix:.1f} (elevated, reducing confidence)")
        if us_vix and us_vix > 30:
            bullish_score *= 0.5
            key_factors.append(f"US VIX={us_vix:.1f} (fear, strong reduction)")

        normalized = bullish_score / total_weight if total_weight else 0.0
        confidence = min(abs(normalized) * 5, 0.90)

        if normalized > 0.015:
            direction = SignalDirection.STRONG_BUY if confidence > 0.65 else SignalDirection.BUY
        elif normalized < -0.015:
            direction = SignalDirection.STRONG_SELL if confidence > 0.65 else SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0.3

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            symbol="NIFTY 50",
            reasoning=f"Global markets weighted signal: score={normalized:.4f}. " + "; ".join(key_factors[:4]),
            key_factors=key_factors,
            india_vix=india_vix,
            supporting_data=data,
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
        )
