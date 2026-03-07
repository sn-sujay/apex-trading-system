"""
APEX Agent 11: RBIIndianMacroAgent
Tracks RBI policy, Indian inflation (CPI/WPI), GDP, IIP data.
"""
from __future__ import annotations
from typing import Dict, Any

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class RBIIndianMacroAgent(APEXBaseAgent):
    """
    Monitors Indian macroeconomic fundamentals:
    - RBI repo rate and stance (hawkish/dovish)
    - CPI inflation vs RBI target (4% +/- 2%)
    - GDP growth trend
    - USD/INR exchange rate
    """

    RBI_TARGET_INFLATION = 4.0
    RBI_UPPER_BAND = 6.0
    RBI_LOWER_BAND = 2.0

    def __init__(self, config=None):
        super().__init__("RBIIndianMacroAgent", "1.0.0", config)

    async def _fetch_data(self) -> Dict[str, Any]:
        import yfinance as yf
        data = {}
        try:
            usdinr = yf.Ticker("USDINR=X")
            hist = usdinr.history(period="30d")
            data["usdinr"] = float(hist["Close"].iloc[-1]) if not hist.empty else 83.0
            data["usdinr_1m_change"] = float(hist["Close"].pct_change().iloc[-1] * 100) if len(hist) > 1 else 0.0
        except Exception:
            data["usdinr"] = 83.0
        # Hardcode latest known macro data (would normally fetch from MOSPI/RBI API)
        data["repo_rate"] = 6.50
        data["cpi_latest"] = 5.1
        data["gdp_latest"] = 7.2
        data["rbi_stance"] = "neutral"  # "hawkish" / "dovish" / "neutral"
        return data

    async def analyze(self) -> AgentSignal:
        data = await self._fetch_data()
        repo_rate = data.get("repo_rate", 6.5)
        cpi = data.get("cpi_latest", 5.0)
        gdp = data.get("gdp_latest", 7.0)
        usdinr = data.get("usdinr", 83.0)
        stance = data.get("rbi_stance", "neutral")

        score = 0.0
        key_factors = []

        # GDP strength
        if gdp > 7:
            score += 0.3
            key_factors.append(f"GDP growth {gdp:.1f}% (strong)")
        elif gdp < 5:
            score -= 0.3
            key_factors.append(f"GDP growth {gdp:.1f}% (weak)")
        else:
            key_factors.append(f"GDP growth {gdp:.1f}% (moderate)")

        # CPI vs target
        if cpi > self.RBI_UPPER_BAND:
            score -= 0.4
            key_factors.append(f"CPI {cpi:.1f}% above RBI upper band (hawkish pressure)")
        elif cpi < self.RBI_LOWER_BAND:
            score += 0.3
            key_factors.append(f"CPI {cpi:.1f}% below lower band (room to cut)")
        elif cpi < self.RBI_TARGET_INFLATION:
            score += 0.2
            key_factors.append(f"CPI {cpi:.1f}% below target (accommodative possible)")
        else:
            key_factors.append(f"CPI {cpi:.1f}% within target band")

        # INR strength
        if usdinr > 85:
            score -= 0.2
            key_factors.append(f"INR weak at {usdinr:.1f}/USD")
        elif usdinr < 82:
            score += 0.1
            key_factors.append(f"INR strong at {usdinr:.1f}/USD")

        # RBI stance
        if stance == "dovish":
            score += 0.25
            key_factors.append("RBI stance: dovish (rate cut bias)")
        elif stance == "hawkish":
            score -= 0.25
            key_factors.append("RBI stance: hawkish (rate hike bias)")

        confidence = min(abs(score) * 1.2, 0.80)
        if score > 0.25:
            direction = SignalDirection.BUY
        elif score < -0.25:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0.35

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            symbol="NIFTY 50",
            reasoning=f"Indian macro: GDP={gdp}%, CPI={cpi}%, Repo={repo_rate}%, INR={usdinr:.1f}",
            key_factors=key_factors,
            timeframe=SignalTimeframe.POSITIONAL,
            asset_class=AssetClass.INDEX,
            supporting_data=data,
        )
