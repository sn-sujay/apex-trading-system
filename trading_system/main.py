"""
APEX Trading Intelligence System -- Main Entrypoint
Bootstraps all agents, infrastructure connections, signal bus, risk engine,
and the FastAPI control plane. Run with:

    uvicorn trading_system.main:app --host 0.0.0.0 --port 8000 --reload

Or directly:

    python -m trading_system.main
"""
from __future__ import annotations
from trading_system.api.server import create_app
from trading_system.agents import (
    IndianMarketDataAgent, GlobalMarketDataAgent, TechnicalAnalysisAgent,
    AlgoStrategyAgent, OptionsDerivativesAgent, MarketRegimeAgent,
    SGXPreMarketAgent, CommoditiesAgent, FundamentalAnalysisAgent,
    FIIDIIFlowAgent, RBIIndianMacroAgent, GlobalMacroAgent,
    IndianNewsEventsAgent, GlobalNewsAgent, SentimentPositioningAgent,
    ZeroDTEExpiryAgent,
)
from trading_system.execution.smart_router import SmartOrderRouter
from trading_system.execution.dhan_executor import DhanExecutor
from trading_system.execution.order_manager import OrderManagementSystem
from trading_system.risk.portfolio_manager import PortfolioManager, Position
from trading_system.risk.volatility_kill_switch import VolatilityKillSwitch
from trading_system.risk.risk_manager import RiskManager
from trading_system.core.signal_schema import SignalDirection
from trading_system.signals.learning_engine import LearningEngine
from trading_system.signals.master_decision_maker import MasterDecisionMaker
from trading_system.signals.conflict_detector import ConflictDetector
from trading_system.signals.signal_bus import SignalBus
from trading_system.data.dhan_feed import DhanDataFeed
from trading_system.data.kafka_setup import KafkaManager
from trading_system.data.redis_client import RedisClient
from trading_system.core.config import Config

import asyncio
import logging
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("apex.main")


app = create_app()


class APEXOrchestrator:
    """Top-level orchestrator -- wires all components and manages lifecycle."""

    def __init__(self):
        self.config = Config()
        self.running = False
        self._tasks: List[asyncio.Task] = []

        self.redis = RedisClient(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT)
        self.kafka = KafkaManager(
            bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS)

        self.signal_bus = SignalBus(redis_client=self.redis)
        self.conflict_detector = ConflictDetector()
        self.learning_engine = LearningEngine(redis_client=self.redis)

        self.executor = DhanExecutor(
            client_id=self.config.DHAN_CLIENT_ID,
            access_token=self.config.DHAN_ACCESS_TOKEN,
        )
        self.risk_manager = RiskManager(config=self.config, redis_client=self.redis, executor=self.executor)
        self.kill_switch = VolatilityKillSwitch(config=self.config)

        self.master_decision = MasterDecisionMaker(
            signal_bus=self.signal_bus,
            conflict_detector=self.conflict_detector,
            learning_engine=self.learning_engine,
            risk_manager=self.risk_manager,
            kill_switch=self.kill_switch
        )

        self.portfolio_manager = PortfolioManager(redis_client=self.redis)

        self.oms = OrderManagementSystem(executor=self.executor)
        self.router = SmartOrderRouter(executor=self.executor, oms=self.oms)

        self.feed = DhanDataFeed(
            client_id=self.config.DHAN_CLIENT_ID,
            access_token=self.config.DHAN_ACCESS_TOKEN,
        )
        self.feed.on("tick", self._handle_tick)

        self.agents = [
            IndianMarketDataAgent(),
            GlobalMarketDataAgent(),
            TechnicalAnalysisAgent(),
            AlgoStrategyAgent(),
            OptionsDerivativesAgent(),
            MarketRegimeAgent(),
            SGXPreMarketAgent(),
            CommoditiesAgent(),
            FundamentalAnalysisAgent(),
            FIIDIIFlowAgent(),
            RBIIndianMacroAgent(),
            GlobalMacroAgent(),
            IndianNewsEventsAgent(),
            GlobalNewsAgent(),
            SentimentPositioningAgent(),
            ZeroDTEExpiryAgent(),
        ]
        for agent in self.agents:
            agent._redis = self.redis
            agent.config = self.config

    def _handle_tick(self, tick_data):
        """Dispatch incoming tick data to all agents."""
        for agent in self.agents:
            try:
                agent.on_tick(tick_data)
            except Exception as e:
                log.warning(f"Agent tick error: {e}")

    async def monitor_and_act(self):
        """Continuous loop: monitors signals for entries and positions for auto-exits."""
        log.info("Starting APEX Decision & Execution loop...")
        while self.running:
            try:
                # 1. Fetch Latest Signals
                signals = self.signal_bus.get_all_signals()
                if not signals:
                    await asyncio.sleep(10)
                    continue

                # 2. Market State Placeholder
                market_data = {"timestamp": datetime.now(timezone.utc).isoformat()}
                
                # 3. Handle AUTO-EXITS (Unsafe trades)
                # Monitor currently held positions in portfolio_manager
                open_positions = self.portfolio_manager.positions
                if open_positions:
                    unsafe_exits = await self.master_decision.monitor_open_positions(open_positions, market_data)
                    for exit_info in unsafe_exits:
                        log.warning(f"AUTO-EXIT: Disposed unsafe position {exit_info['symbol']} | {exit_info['reason']}")
                        # 1. Close in local Portfolio
                        # In a real environment, we'd fetch the current LTP from feed
                        exit_price = 0.0 # TODO: Get LTP
                        self.portfolio_manager.close_position(exit_info["position_id"], exit_price)
                        # 2. Trigger Broker Order
                        # await self.oms.close_all_for_symbol(exit_info['symbol'])

                # 4. Handle NEW ENTRIES (Ranking & Selection)
                decision = await self.master_decision.decide(market_data)
                
                if decision.final_direction != SignalDirection.NEUTRAL:
                    # Validating only the 'Best' decision (Consensus)
                    # MasterDecisionMaker already aggregates and weights the best signals
                    
                    # Risk Check
                    # We pass a proposed transaction based on the decision
                    proposed = {
                        "symbol": getattr(decision, "symbol", "NIFTY BANK"), # Fallback to BankNifty
                        "direction": decision.final_direction.value,
                        "entry_price": market_data.get("price", 0), # placeholder
                        "stop_loss": market_data.get("price", 0) * 0.98 if decision.final_direction == SignalDirection.BULLISH else market_data.get("price", 0) * 1.02
                    }
                    
                    approved, reason, trade = self.risk_manager.validate_signal({}, proposed)
                    
                    if approved and trade["quantity"] > 0:
                        log.info(f"LIVE SIGNAL APPROVED: {trade['symbol']} {trade['direction']} | Qty: {trade['quantity']} | Reason: {decision.reasoning}")
                        
                        # EXECUTION
                        # order = self.oms.create_order(...)
                        # await self.router.route(order)
                        
                        # PORTFOLIO UPDATE
                        new_pos = Position(
                            symbol=trade["symbol"],
                            direction=trade["direction"],
                            entry_price=trade["entry_price"],
                            quantity=trade["quantity"],
                            stop_loss=trade.get("stop_loss", 0)
                        )
                        self.portfolio_manager.add_position(new_pos)
                    else:
                        if trade.get("quantity") == 0:
                            log.debug(f"Trade suppressed: Risk limit or insufficient funds for {proposed['symbol']}")
                        else:
                            log.debug(f"Signal rejected by Risk: {reason}")

            except Exception as e:
                log.error(f"Error in Orchestrator Loop: {e}", exc_info=True)
            
            await asyncio.sleep(15) # Faster cycle for live monitoring

    async def start(self):
        log.info("APEX Orchestrator starting...")
        self.running = True
        self.feed.connect()
        
        # 1. Start Agents
        for agent in self.agents:
            t = asyncio.create_task(agent.run_forever())
            self._tasks.append(t)
            
        # 2. Start Decision Loop
        self._tasks.append(asyncio.create_task(self.monitor_and_act()))
        
        log.info(f"APEX ONLINE | {len(self.agents)} Agents Active | Decision Loop Running")

    async def stop(self):
        log.info("APEX Orchestrator stopping...")
        self.running = False
        self.feed.disconnect()
        for t in self._tasks:
            t.cancel()
        log.info("APEX OFFLINE")


@app.on_event("startup")
async def startup():
    app.state.orchestrator = APEXOrchestrator()
    await app.state.orchestrator.start()


@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "orchestrator"):
        await app.state.orchestrator.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "trading_system.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False)
