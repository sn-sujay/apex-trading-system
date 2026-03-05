"""
FundamentalAnalysis Agent — evaluates company/index fundamentals.
Tracks P/E, P/B, EPS growth, sector rotation, FII/DII flows, and earnings calendar.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class FundamentalAnalysisAgent(APEXBaseAgent):
    """
    Layer 3 Fundamental Agent: sector rotation analysis, valuation scoring,
    earnings impact assessment, and long-term trend identification.
    """

    AGENT_NAME = "FundamentalAnalysisAgent"
    AGENT_LAYER = 3
    SIGNAL_WEIGHT = 0.10

    NIFTY50_FAIR_PE = 20.0
    NIFTY50_HISTORICAL_MEAN_PE = 22.5

    SECTOR_WEIGHTS = {
        "financial_services": 0.365,
        "it": 0.130,
        "oil_gas": 0.115,
        "consumer_goods": 0.085,
        "automobile": 0.065,
        "metals": 0.040,
        "pharma": 0.038,
        "power": 0.035,
        "telecom": 0.030,
        "realty": 0.020,
    }

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        valuation_score = self._score_valuation(market_data)
        earnings_score = self._score_earnings_momentum(market_data)
        sector_score = self._score_sector_rotation(market_data)
        macro_score = self._score_macro_linkage(market_data)

        total_score = (
            valuation_score * 0.30
            + earnings_score * 0.35
            + sector_score * 0.20
            + macro_score * 0.15
        )

        direction = (
            SignalDirection.BULLISH if total_score > 15
            else SignalDirection.BEARISH if total_score < -15
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total_score) / 60, 1.0),
            timeframe=SignalTimeframe.POSITIONAL,
            asset_class=AssetClass.INDEX,
            reasoning=(
                f"Valuation: {valuation_score:.1f} | Earnings: {earnings_score:.1f} | "
                f"Sector: {sector_score:.1f} | Macro: {macro_score:.1f}"
            ),
            metadata={
                "valuation_score": valuation_score,
                "earnings_score": earnings_score,
                "sector_score": sector_score,
                "macro_score": macro_score,
                "total_score": total_score,
            },
        )

    def _score_valuation(self, data: Dict) -> float:
        pe = data.get("nifty_pe", self.NIFTY50_FAIR_PE)
        pb = data.get("nifty_pb", 3.0)
        score = 0.0
        if pe < 16:
            score += 30
        elif pe < 20:
            score += 15
        elif pe < 25:
            score += 0
        elif pe < 30:
            score -= 15
        else:
            score -= 30
        if pb < 2.5:
            score += 10
        elif pb > 4.5:
            score -= 10
        return score

    def _score_earnings_momentum(self, data: Dict) -> float:
        eps_growth_qoq = data.get("eps_growth_qoq", 0)
        earnings_beat_ratio = data.get("earnings_beat_ratio", 0.5)
        revenue_growth = data.get("revenue_growth_yoy", 0)
        score = 0.0
        score += min(eps_growth_qoq * 2, 25)
        score += (earnings_beat_ratio - 0.5) * 40
        score += min(revenue_growth * 1.5, 15)
        return max(min(score, 50), -50)

    def _score_sector_rotation(self, data: Dict) -> float:
        sector_momentum = data.get("sector_momentum", {})
        defensive_sectors = {"pharma", "fmcg", "utilities"}
        cyclical_sectors = {"it", "financial_services", "automobile", "metals"}
        score = 0.0
        for sector, momentum in sector_momentum.items():
            weight = self.SECTOR_WEIGHTS.get(sector, 0.02)
            if sector in cyclical_sectors and momentum > 0:
                score += momentum * weight * 100
            elif sector in defensive_sectors and momentum < 0:
                score += abs(momentum) * weight * 50
        return max(min(score, 30), -30)

    def _score_macro_linkage(self, data: Dict) -> float:
        gdp_growth = data.get("gdp_growth", 6.0)
        iip_growth = data.get("iip_growth", 3.0)
        cpi = data.get("cpi", 5.0)
        score = 0.0
        if gdp_growth > 7:
            score += 20
        elif gdp_growth > 6:
            score += 10
        elif gdp_growth < 5:
            score -= 15
        if cpi < 4:
            score += 10
        elif cpi > 6:
            score -= 15
        score += min((iip_growth - 3) * 3, 10)
        return max(min(score, 30), -30)
