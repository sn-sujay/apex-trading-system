"""
APEX Trading Intelligence System — Main Entrypoint
Bootstraps all agents, infrastructure connections, signal bus, risk engine,
and the FastAPI control plane. Run with:

    uvicorn trading_system.main:app --host 0.0.0.0 --port 8000 --reload

Or directly:

    python -m trading_system.main
"""
from __future__ import annotations

import asyncio
import logging
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("apex.main")

from trading_system.core.config import Config
from trading_system.data.redis_client import RedisClient
from trading_system.data.kafka_setup import KafkaManager
from trading_system.data.kite_feed import KiteWebSocketFeed
from trading_system.signals.signal_bus import SignalBus
from trading_system.signals.conflict_detector import ConflictDetector
from trading_system.signals.master_decision_maker import MasterDecisionMaker
from trading_system.signals.learning_engine import LearningEngine
from trading_system.risk.risk_manager import RiskManager
from trading_system.risk.volatility_kill_switch import VolatilityKillSwitch
from trading_system.risk.portfolio_manager import PortfolioManager
from trading_system.execution.order_manager import OrderManagementSystem
from trading_system.execution.kite_executor import KiteExecutor
from trading_system.execution.smart_router import SmartOrderRouter
from trading_system.agents import (
    IndianMarketDataAgent, GlobalMarketDataAgent, TechnicalAnalysisAgent,
    AlgoStrategyAgent, OptionsDerivativesAgent, MarketRegimeAgent,
    SGXPreMarketAgent, CommoditiesAgent, FundamentalAnalysisAgent,
    FIIDIIFlowAgent, RBIIndianMacroAgent, GlobalMacroAgent,
    IndianNewsEventsAgent, GlobalNewsAgent, SentimentPositioningAgent,
    ZeroDTEExpiryAgent,
)
from trading_system.api.server import create_app

app = create_app()


class APEXOrchestrator:
    """Top-level orchestrator — wires all components and manages lifecycle."""

    def __init__(self):
        self.config = Config()
        self.running = False
        self._tasks: List[asyncio.Task] = []

        self.redis = RedisClient(host=self.config.REDIS_HOST, port=self.config.REDIS_PORT)
        self.kafka = KafkaManager(bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS)

        self.signal_bus = SignalBus(redis_client=self.redis)
        self.conflict_detector = ConflictDetector()
        self.learning_engine = LearningEngine(redis_client=self.redis)
        self.master_decision = MasterDecisionMaker(
            signal_bus=self.signal_bus,
            conflict_detector=self.conflict_detector,
            learning_engine=self.learning_engine,
        )

        self.risk_manager = RiskManager(config=self.config)
        self.kill_switch = VolatilityKillSwitch(config=self.config)
        self.portfolio_manager = PortfolioManager(config=self.config)

        self.kite_executor = KiteExecutor(config=self.config)
        self.smart_router = SmartOrderRouter(executor=self.kite_executor)
        self.oms = OrderManagementSystem(
            router=self.smart_router,
            risk_manager=self.risk_manager,
            portfolio_manager=self.portfolio_manager,
        )

        self.agents = [
            IndianMarketDataAgent(config=self.config, signal_bus=self.signal_bus),
            GlobalMarketDataAgent(config=self.config, signal_bus=self.signal_bus),
            TechnicalAnalysisAgent(config=self.config, signal_bus=self.signal_bus),
            AlgoStrategyAgent(config=self.config, signal_bus=self.signal_bus),
            OptionsDerivativesAgent(config=self.config, signal_bus=self.signal_bus),
            MarketRegimeAgent(config=self.config, signal_bus=self.signal_bus),
            SGXPreMarketAgent(config=self.config, signal_bus=self.signal_bus),
            CommoditiesAgent(config=self.config, signal_bus=self.signal_bus),
            FundamentalAnalysisAgent(config=self.config, signal_bus=self.signal_bus),
            FIIDIIFlowAgent(config=self.config, signal_bus=self.signal_bus),
            RBIIndianMacroAgent(config=self.config, signal_bus=self.signal_bus),
            GlobalMacroAgent(config=self.config, signal_bus=self.signal_bus),
            IndianNewsEventsAgent(config=self.config, signal_bus=self.signal_bus),
            GlobalNewsAgent(config=self.config, signal_bus=self.signal_bus),
            SentimentPositioningAgent(config=self.config, signal_bus=self.signal_bus),
            ZeroDTEExpiryAgent(config=self.config, signal_bus=self.signal_bus),
        ]
        log.info(f"APEXOrchestrator initialised — {len(self.agents)} agents loaded")

    async def start(self):
        self.running = True
        log.info("Starting APEX Trading Intelligence System...")
        await self.redis.connect()
        await self.kafka.create_topics()
        for agent in self.agents:
            task = asyncio.create_task(agent.run(), name=agent.__class__.__name__)
            self._tasks.append(task)
            log.info(f"  Agent started: {agent.__class__.__name__}")
        self._tasks.append(asyncio.create_task(self.master_decision.run(), name="MasterDecisionMaker"))
        self._tasks.append(asyncio.create_task(self.kill_switch.monitor(), name="VolatilityKillSwitch"))
        log.info(f"APEX running — {len(self._tasks)} async tasks active")
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def stop(self):
        log.info("Shutting down APEX...")
        self.running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.redis.disconnect()
        log.info("APEX shutdown complete.")


orchestrator: APEXOrchestrator | None = None


@app.on_event("startup")
async def on_startup():
    global orchestrator
    orchestrator = APEXOrchestrator()
    asyncio.create_task(orchestrator.start())
    log.info("APEX Orchestrator started via FastAPI startup hook")


@app.on_event("shutdown")
async def on_shutdown():
    if orchestrator:
        await orchestrator.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("trading_system.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
