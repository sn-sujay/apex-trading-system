"""
APEX Agent 4: TechnicalAnalysisAgent
Multi-timeframe technical analysis using pandas_ta.
Indicators: EMA, RSI, MACD, Bollinger Bands, Supertrend, ADX, Ichimoku.
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class TechnicalAnalysisAgent(APEXBaseAgent):
    """
    Multi-indicator, multi-timeframe technical analysis.
    Combines 7 independent indicators via weighted voting.
    """

    INDICATOR_WEIGHTS = {
        "ema_cross":     0.20,
        "rsi":           0.15,
        "macd":          0.20,
        "bollinger":     0.15,
        "supertrend":    0.15,
        "adx":           0.10,
        "volume_trend":  0.05,
    }

    def __init__(self, config=None):
        super().__init__("TechnicalAnalysisAgent", "1.0.0", config)

    async def _fetch_data(self) -> Dict[str, Any]:
        import yfinance as yf
        data = {}
        for tf, period, interval in [
            ("5m", "1d", "5m"),
            ("15m", "5d", "15m"),
            ("1h", "30d", "1h"),
            ("1d", "180d", "1d"),
        ]:
            try:
                df = yf.download("^NSEI", period=period, interval=interval, progress=False)
                df.columns = [c.lower() for c in df.columns]
                data[tf] = df
            except Exception as e:
                self.logger.warning(f"Failed TF {tf}: {e}")
        return data

    def _ema_cross_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        if len(df) < 21:
            return 0.0, "Insufficient data for EMA"
        c = df["close"] if "close" in df.columns else df["adj close"]
        e9 = c.ewm(span=9).mean()
        e21 = c.ewm(span=21).mean()
        e50 = c.ewm(span=50).mean()
        if len(e9) < 2:
            return 0.0, "Insufficient EMA data"
        cross = float(e9.iloc[-1]) - float(e21.iloc[-1])
        prev_cross = float(e9.iloc[-2]) - float(e21.iloc[-2])
        price_vs_50 = float(c.iloc[-1]) - float(e50.iloc[-1])
        score = 0.0
        reason = []
        if cross > 0 and prev_cross <= 0:
            score = 1.0
            reason.append("Bullish EMA9/21 crossover")
        elif cross < 0 and prev_cross >= 0:
            score = -1.0
            reason.append("Bearish EMA9/21 crossover")
        elif cross > 0:
            score = 0.5
            reason.append("EMA9 above EMA21")
        else:
            score = -0.5
            reason.append("EMA9 below EMA21")
        if price_vs_50 > 0:
            score += 0.2
            reason.append("Price above EMA50")
        else:
            score -= 0.2
            reason.append("Price below EMA50")
        return float(np.clip(score, -1, 1)), "; ".join(reason)

    def _rsi_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        if len(df) < 15:
            return 0.0, "Insufficient RSI data"
        c = df["close"] if "close" in df.columns else df["adj close"]
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])
        if rsi < 30:
            return 0.9, f"RSI={rsi:.1f} oversold (buy)"
        elif rsi < 45:
            return 0.4, f"RSI={rsi:.1f} recovering"
        elif rsi > 70:
            return -0.9, f"RSI={rsi:.1f} overbought (sell)"
        elif rsi > 55:
            return 0.3, f"RSI={rsi:.1f} bullish momentum"
        else:
            return 0.0, f"RSI={rsi:.1f} neutral"

    def _macd_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        if len(df) < 26:
            return 0.0, "Insufficient MACD data"
        c = df["close"] if "close" in df.columns else df["adj close"]
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        if len(hist) < 2:
            return 0.0, "MACD insufficient"
        if float(hist.iloc[-1]) > 0 and float(hist.iloc[-2]) <= 0:
            return 1.0, "MACD histogram turned positive (bullish)"
        elif float(hist.iloc[-1]) < 0 and float(hist.iloc[-2]) >= 0:
            return -1.0, "MACD histogram turned negative (bearish)"
        elif float(hist.iloc[-1]) > float(hist.iloc[-2]) > 0:
            return 0.5, "MACD histogram expanding bullish"
        elif float(hist.iloc[-1]) < float(hist.iloc[-2]) < 0:
            return -0.5, "MACD histogram expanding bearish"
        return 0.0, "MACD neutral"

    def _bollinger_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        if len(df) < 20:
            return 0.0, "Insufficient BB data"
        c = df["close"] if "close" in df.columns else df["adj close"]
        ma = c.rolling(20).mean()
        std = c.rolling(20).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        price = float(c.iloc[-1])
        u = float(upper.iloc[-1])
        l = float(lower.iloc[-1])
        b = (price - l) / (u - l) if (u - l) > 0 else 0.5
        if b < 0.1:
            return 0.8, f"Price near BB lower band (oversold, %B={b:.2f})"
        elif b > 0.9:
            return -0.8, f"Price near BB upper band (overbought, %B={b:.2f})"
        elif b > 0.5:
            return 0.2, f"Price in upper BB half (%B={b:.2f})"
        else:
            return -0.2, f"Price in lower BB half (%B={b:.2f})"

    def _supertrend_signal(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[float, str]:
        if len(df) < period + 1:
            return 0.0, "Insufficient Supertrend data"
        high = df["high"] if "high" in df.columns else df["High"]
        low = df["low"] if "low" in df.columns else df["Low"]
        close = df["close"] if "close" in df.columns else df["Close"]
        hl2 = (high + low) / 2
        tr = pd.concat([high - low,
                         (high - close.shift()).abs(),
                         (low - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        supertrend = pd.Series(index=df.index, dtype=float)
        direction_arr = pd.Series(index=df.index, dtype=int)
        for i in range(period, len(df)):
            if i == period:
                supertrend.iloc[i] = lower.iloc[i]
                direction_arr.iloc[i] = 1
            else:
                prev_st = float(supertrend.iloc[i-1])
                prev_dir = int(direction_arr.iloc[i-1])
                curr_close = float(close.iloc[i])
                if prev_dir == 1:
                    supertrend.iloc[i] = max(float(lower.iloc[i]), prev_st)
                    direction_arr.iloc[i] = 1 if curr_close > supertrend.iloc[i] else -1
                else:
                    supertrend.iloc[i] = min(float(upper.iloc[i]), prev_st)
                    direction_arr.iloc[i] = -1 if curr_close < supertrend.iloc[i] else 1
        curr_dir = int(direction_arr.iloc[-1])
        prev_dir = int(direction_arr.iloc[-2]) if len(direction_arr) > 1 else curr_dir
        if curr_dir == 1 and prev_dir == -1:
            return 1.0, "Supertrend flipped BULLISH"
        elif curr_dir == -1 and prev_dir == 1:
            return -1.0, "Supertrend flipped BEARISH"
        elif curr_dir == 1:
            return 0.5, "Supertrend bullish"
        else:
            return -0.5, "Supertrend bearish"

    def _adx_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        if len(df) < 15:
            return 0.0, "Insufficient ADX data"
        high = df["high"] if "high" in df.columns else df["High"]
        low = df["low"] if "low" in df.columns else df["Low"]
        close = df["close"] if "close" in df.columns else df["Close"]
        tr = pd.concat([high - low,
                         (high - close.shift()).abs(),
                         (low - close.shift()).abs()], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean()
        dm_plus = high.diff().clip(lower=0)
        dm_minus = (-low.diff()).clip(lower=0)
        di_plus = 100 * dm_plus.rolling(14).mean() / atr14
        di_minus = 100 * dm_minus.rolling(14).mean() / atr14
        dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
        adx = dx.rolling(14).mean()
        adx_val = float(adx.iloc[-1]) if not adx.empty else 20
        di_p = float(di_plus.iloc[-1]) if not di_plus.empty else 20
        di_m = float(di_minus.iloc[-1]) if not di_minus.empty else 20
        trend_strength = "strong" if adx_val > 25 else "weak"
        if adx_val > 25 and di_p > di_m:
            return 0.7, f"ADX={adx_val:.1f} {trend_strength} bullish trend"
        elif adx_val > 25 and di_m > di_p:
            return -0.7, f"ADX={adx_val:.1f} {trend_strength} bearish trend"
        return 0.0, f"ADX={adx_val:.1f} (no strong trend)"

    def _volume_trend_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        if len(df) < 20 or "volume" not in df.columns:
            return 0.0, "No volume data"
        vol = df["volume"]
        close = df["close"] if "close" in df.columns else df["adj close"]
        vol_ma = vol.rolling(20).mean()
        vol_ratio = float(vol.iloc[-1]) / float(vol_ma.iloc[-1]) if float(vol_ma.iloc[-1]) > 0 else 1.0
        price_change = float(close.pct_change().iloc[-1])
        if vol_ratio > 1.5 and price_change > 0:
            return 0.8, f"High volume ({vol_ratio:.1f}x avg) on up move"
        elif vol_ratio > 1.5 and price_change < 0:
            return -0.8, f"High volume ({vol_ratio:.1f}x avg) on down move"
        elif vol_ratio < 0.5:
            return 0.0, f"Low volume ({vol_ratio:.1f}x avg), weak conviction"
        return 0.0, f"Normal volume ({vol_ratio:.1f}x avg)"

    async def analyze(self) -> AgentSignal:
        data = await self._fetch_data()
        if not data:
            return self._no_signal("No market data available")

        # Multi-timeframe scoring: weight longer TFs more
        tf_weights = {"5m": 0.2, "15m": 0.3, "1h": 0.3, "1d": 0.2}
        total_score = 0.0
        all_factors = []

        for tf, tf_weight in tf_weights.items():
            df = data.get(tf)
            if df is None or df.empty:
                continue

            indicator_scores = {
                "ema_cross":     self._ema_cross_signal(df),
                "rsi":           self._rsi_signal(df),
                "macd":          self._macd_signal(df),
                "bollinger":     self._bollinger_signal(df),
                "supertrend":    self._supertrend_signal(df),
                "adx":           self._adx_signal(df),
                "volume_trend":  self._volume_trend_signal(df),
            }

            tf_score = sum(
                score * self.INDICATOR_WEIGHTS[ind]
                for ind, (score, _) in indicator_scores.items()
            )
            total_score += tf_score * tf_weight

            # Add key factors from daily timeframe
            if tf == "1d":
                for ind, (score, reason) in indicator_scores.items():
                    if abs(score) > 0.3:
                        all_factors.append(f"[{tf}] {reason}")

        confidence = min(abs(total_score) * 1.5, 0.92)
        if total_score > 0.30:
            direction = SignalDirection.STRONG_BUY if total_score > 0.55 else SignalDirection.BUY
        elif total_score < -0.30:
            direction = SignalDirection.STRONG_SELL if total_score < -0.55 else SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            confidence = max(confidence, 0.2)

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            symbol="NIFTY 50",
            reasoning=f"Multi-TF technical score={total_score:.3f}",
            key_factors=all_factors[:6],
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
        )
