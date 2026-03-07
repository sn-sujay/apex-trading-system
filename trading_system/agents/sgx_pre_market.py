"""
SGX Pre-Market Agent — monitors SGX Nifty / GIFT Nifty for overnight gap prediction.
Runs before Indian market open (8:00–9:15 AM IST) to set pre-market directional bias.
"""
from __future__ import annotations
import httpx
from typing import Any, Dict
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class SGXPreMarketAgent(APEXBaseAgent):
    """
    Monitors GIFT Nifty (formerly SGX Nifty) futures for pre-market gap estimation.
    Fetches Dow futures, S&P futures, Nikkei, and Hang Seng to build opening bias.
    """

    AGENT_NAME = "SGXPreMarketAgent"
    AGENT_LAYER = 1
    SIGNAL_WEIGHT = 0.08

    GIFT_NIFTY_URL = "https://query1.finance.yahoo.com/v8/finance/chart/NIFTY50.NS"
    FUTURES_SYMBOLS = {
        "sp500_fut": "ES=F",
        "dow_fut": "YM=F",
        "nasdaq_fut": "NQ=F",
        "nikkei": "^N225",
        "hang_seng": "^HSI",
        "crude": "CL=F",
        "usdinr": "USDINR=X",
    }

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        gift_nifty = market_data.get("gift_nifty_price", 0)
        nifty_prev_close = market_data.get("nifty_prev_close", 0)
        global_futures = market_data.get("global_futures", {})

        gap_score = self._calculate_gap_score(gift_nifty, nifty_prev_close)
        global_score = self._calculate_global_score(global_futures)
        total_score = (gap_score * 0.6) + (global_score * 0.4)

        direction = (
            SignalDirection.BULLISH if total_score > 10
            else SignalDirection.BEARISH if total_score < -10
            else SignalDirection.NEUTRAL
        )

        gap_pct = ((gift_nifty - nifty_prev_close) / nifty_prev_close * 100) if nifty_prev_close else 0

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total_score) / 80, 1.0),
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
            reasoning=f"GIFT Nifty gap: {gap_pct:+.2f}% | Global score: {global_score:.1f}",
            metadata={
                "gift_nifty": gift_nifty,
                "gap_pct": gap_pct,
                "gap_score": gap_score,
                "global_score": global_score,
                "total_score": total_score,
                "global_futures": global_futures,
            },
        )

    def _calculate_gap_score(self, gift_price: float, prev_close: float) -> float:
        if not prev_close or not gift_price:
            return 0.0
        gap_pct = (gift_price - prev_close) / prev_close * 100
        if gap_pct > 1.0:
            return min(gap_pct * 20, 60)
        elif gap_pct < -1.0:
            return max(gap_pct * 20, -60)
        return gap_pct * 10

    def _calculate_global_score(self, futures: Dict[str, float]) -> float:
        score = 0.0
        weights = {
            "sp500_change": 0.35,
            "dow_change": 0.20,
            "nasdaq_change": 0.20,
            "nikkei_change": 0.15,
            "hang_seng_change": 0.10,
        }
        for key, weight in weights.items():
            change = futures.get(key, 0)
            score += change * weight * 10
        crude_change = futures.get("crude_change", 0)
        if crude_change > 2:
            score -= 5
        elif crude_change < -2:
            score += 3
        usdinr_change = futures.get("usdinr_change", 0)
        if usdinr_change > 0.5:
            score -= 5
        elif usdinr_change < -0.5:
            score += 5
        return max(min(score, 60), -60)

    async def fetch_gift_nifty_data(self) -> Dict[str, float]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/^NSEI",
                    params={"interval": "1m", "range": "1d"},
                )
                data = resp.json()
                result = data["chart"]["result"][0]
                meta = result["meta"]
                return {
                    "price": meta.get("regularMarketPrice", 0),
                    "prev_close": meta.get("previousClose", 0),
                    "change_pct": (
                        (meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0))
                        / meta.get("previousClose", 1) * 100
                    ),
                }
            except Exception as e:
                return {"price": 0, "prev_close": 0, "change_pct": 0, "error": str(e)}
