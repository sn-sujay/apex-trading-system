# APEX Trading Intelligence System — core package
from .signal_schema import (
    AgentSignal, ConsensusDecision,
    SignalDirection, SignalTimeframe, AssetClass, MarketRegime
)
from .config import APEXConfig, settings
from .base_agent import APEXBaseAgent

__all__ = [
    "AgentSignal", "ConsensusDecision",
    "SignalDirection", "SignalTimeframe", "AssetClass", "MarketRegime",
    "APEXConfig", "APEXBaseAgent",
    "SignalSchema", "Config", "settings"
]

SignalSchema = AgentSignal
Config = APEXConfig
