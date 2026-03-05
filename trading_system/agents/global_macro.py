"""
GlobalMacro Agent — synthesizes US Fed policy, DXY, treasury yields,
commodity supercycles, and EM capital flows for top-down directional bias.
"""
from __future__ import annotations
from typing import Any, Dict
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class GlobalMacroAgent(APEXBaseAgent):
    """
    Layer 3 Macro Agent: monitors Fed dot plot, yield curve, DXY,
    global liquidity, and commodity cycles to set macro overlay.
    """

    AGENT_NAME = "GlobalMacroAgent"
    AGENT_LAYER = 3
    SIGNAL_WEIGHT = 0.08

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        fed_score = self._score_fed_policy(market_data)
        yield_score = self._score_yield_curve(market_data)
        dxy_score = self._score_dxy_impact(market_data)
        liquidity_score = self._score_global_liquidity(market_data)
        em_score = self._score_em_flows(market_data)

        total = (
            fed_score * 0.30
            + yield_score * 0.20
            + dxy_score * 0.20
            + liquidity_score * 0.15
            + em_score * 0.15
        )

        direction = (
            SignalDirection.BULLISH if total > 10
            else SignalDirection.BEARISH if total < -10
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total) / 50, 1.0),
            timeframe=SignalTimeframe.POSITIONAL,
            asset_class=AssetClass.INDEX,
            reasoning=(
                f"Fed: {fed_score:.1f} | Yields: {yield_score:.1f} | "
                f"DXY: {dxy_score:.1f} | Liquidity: {liquidity_score:.1f} | EM: {em_score:.1f}"
            ),
            metadata={
                "fed_score": fed_score, "yield_score": yield_score,
                "dxy_score": dxy_score, "liquidity_score": liquidity_score,
                "em_score": em_score, "total": total,
            },
        )

    def _score_fed_policy(self, data: Dict) -> float:
        fed_stance = data.get("fed_stance", "neutral")
        rate_change_bps = data.get("expected_rate_change_bps", 0)
        score_map = {"dovish": 30, "neutral": 0, "hawkish": -30}
        score = score_map.get(fed_stance, 0)
        if rate_change_bps < -25:
            score += 20
        elif rate_change_bps > 25:
            score -= 20
        return score

    def _score_yield_curve(self, data: Dict) -> float:
        us10y = data.get("us_10y_yield", 4.0)
        us2y = data.get("us_2y_yield", 4.2)
        spread = us10y - us2y
        if spread > 0.5:
            return 20
        elif spread > 0:
            return 10
        elif spread > -0.5:
            return -10
        else:
            return -25

    def _score_dxy_impact(self, data: Dict) -> float:
        dxy_change = data.get("dxy_1d_change", 0)
        if dxy_change > 0.5:
            return -20
        elif dxy_change > 0.2:
            return -10
        elif dxy_change < -0.5:
            return 20
        elif dxy_change < -0.2:
            return 10
        return 0

    def _score_global_liquidity(self, data: Dict) -> float:
        m2_growth = data.get("global_m2_growth", 0)
        fed_balance_sheet_change = data.get("fed_bs_change_bn", 0)
        score = 0.0
        score += min(m2_growth * 3, 15)
        if fed_balance_sheet_change > 0:
            score += 10
        elif fed_balance_sheet_change < -50:
            score -= 15
        return max(min(score, 25), -25)

    def _score_em_flows(self, data: Dict) -> float:
        em_etf_flow = data.get("em_etf_flow_bn", 0)
        india_fpi_flow = data.get("india_fpi_weekly_cr", 0)
        score = 0.0
        if em_etf_flow > 1:
            score += 15
        elif em_etf_flow < -1:
            score -= 15
        if india_fpi_flow > 2000:
            score += 10
        elif india_fpi_flow < -2000:
            score -= 10
        return max(min(score, 25), -25)
