"""
IndianNewsEvents Agent — parses NSE/BSE announcements, SEBI circulars,
RBI bulletins, earnings releases, and corporate actions for event-driven signals.
"""
from __future__ import annotations
from typing import Any, Dict, List
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class IndianNewsEventsAgent(APEXBaseAgent):
    """
    Layer 4 Sentiment/Event Agent: corporate actions, policy events,
    budget announcements, and NSE/BSE exchange notices.
    """

    AGENT_NAME = "IndianNewsEventsAgent"
    AGENT_LAYER = 4
    SIGNAL_WEIGHT = 0.07

    HIGH_IMPACT_KEYWORDS = [
        "rbi rate", "repo rate", "monetary policy", "budget", "fiscal deficit",
        "rbi governor", "sebi order", "nse halt", "bse halt", "circuit breaker",
        "gdp", "iip data", "cpi inflation", "wpi inflation", "trade deficit",
        "fpo", "ipo listing", "block deal", "open offer", "buyback",
        "earnings beat", "earnings miss", "guidance upgrade", "guidance cut",
        "promoter pledge", "promoter buying", "insider buying",
        "merger", "acquisition", "demerger", "rights issue",
    ]

    BEARISH_KEYWORDS = [
        "fraud", "scam", "ed raid", "it raid", "sebi ban", "npa surge",
        "default", "insolvency", "recall", "drug recall", "plant shutdown",
        "promoter pledge increase", "rating downgrade", "ban",
    ]

    BULLISH_KEYWORDS = [
        "buyback", "dividend", "bonus shares", "stock split", "promoter buying",
        "rating upgrade", "order win", "new contract", "capacity expansion",
        "export approval", "fda approval", "nifty inclusion",
    ]

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        events = market_data.get("indian_events", [])
        corporate_actions = market_data.get("corporate_actions", [])
        policy_calendar = market_data.get("policy_calendar", {})

        event_score = self._score_events(events)
        corporate_score = self._score_corporate_actions(corporate_actions)
        policy_score = self._score_policy_calendar(policy_calendar)

        total = event_score * 0.40 + corporate_score * 0.35 + policy_score * 0.25
        direction = (
            SignalDirection.BULLISH if total > 10
            else SignalDirection.BEARISH if total < -10
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total) / 50, 1.0),
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
            reasoning=(
                f"Events: {event_score:.1f} | Corporate: {corporate_score:.1f} | "
                f"Policy: {policy_score:.1f}"
            ),
            metadata={
                "event_score": event_score,
                "corporate_score": corporate_score,
                "policy_score": policy_score,
                "high_impact_events": [e for e in events if e.get("impact") == "HIGH"],
            },
        )

    def _score_events(self, events: List[Dict]) -> float:
        score = 0.0
        for event in events:
            headline = event.get("headline", "").lower()
            impact = event.get("impact", "LOW")
            event.get("sentiment", "neutral")
            weight = {"HIGH": 15, "MEDIUM": 8, "LOW": 3}.get(impact, 3)
            for kw in self.BULLISH_KEYWORDS:
                if kw in headline:
                    score += weight
                    break
            for kw in self.BEARISH_KEYWORDS:
                if kw in headline:
                    score -= weight * 1.5
                    break
        return max(min(score, 50), -50)

    def _score_corporate_actions(self, actions: List[Dict]) -> float:
        score = 0.0
        positive_actions = {"buyback", "dividend", "bonus", "split", "rights"}
        negative_actions = {"pledge_increase", "promoter_sell", "block_deal_sell"}
        for action in actions:
            action_type = action.get("type", "").lower()
            if any(pa in action_type for pa in positive_actions):
                score += 10
            elif any(na in action_type for na in negative_actions):
                score -= 10
        return max(min(score, 30), -30)

    def _score_policy_calendar(self, calendar: Dict) -> float:
        score = 0.0
        days_to_mpc = calendar.get("days_to_rbi_mpc", 30)
        mpc_expected_action = calendar.get("mpc_expected", "hold")
        days_to_budget = calendar.get("days_to_budget", 365)
        if days_to_mpc <= 2:
            if mpc_expected_action == "cut":
                score += 20
            elif mpc_expected_action == "hike":
                score -= 20
            else:
                score -= 5
        if days_to_budget <= 7:
            score += 5
        return score
