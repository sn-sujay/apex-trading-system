
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .apex_redis import get_intelligence_db

logger = logging.getLogger("apex.core.memory")

class ExperienceMemory:
    """
    Long-term memory bank for agents.
    Stores past 'Lessons Learned' and retrieves them based on current market regime.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.db = get_intelligence_db()
        self.max_memories = 10
        
    def _get_key(self, regime: str) -> str:
        return f"memory:{self.agent_name}:{regime}"

    async def store_experience(self, regime: str, experience: Dict[str, Any]):
        """
        Stores a successful or failed reasoning cycle.
        experience: {
            "timestamp": ...,
            "factors": ...,
            "reasoning": ...,
            "outcome": "SUCCESS" | "FAILURE",
            "pnl_pct": ...
        }
        """
        key = self._get_key(regime)
        try:
            # Get existing memories for this regime
            existing_raw = await self.db.get(key)
            memories = json.loads(existing_raw) if existing_raw else []
            
            # Append new experience
            experience["timestamp"] = datetime.now(timezone.utc).isoformat()
            memories.insert(0, experience)
            
            # Keep only the freshest/most relevant
            memories = memories[:self.max_memories]
            
            await self.db.set(key, json.dumps(memories), ex=86400 * 30) # 30 day memory
            logger.info(f"Stored new experience for {self.agent_name} in {regime} regime.")
        except Exception as e:
            logger.error(f"Failed to store experience: {e}")

    async def retrieve_relevant_experiences(self, regime: str) -> List[Dict[str, Any]]:
        """
        Retrieves past experiences for the given regime to provide context.
        """
        key = self._get_key(regime)
        try:
            raw = await self.db.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to retrieve experiences: {e}")
        return []

    def format_experiences_for_prompt(self, experiences: List[Dict[str, Any]]) -> str:
        """
        Converts experiences into a bulleted string for LLM context.
        """
        if not experiences:
            return "No prior experience in this market regime."
            
        formatted = "PAST EXPERIENCES IN THIS REGIME:\n"
        for exp in experiences[:3]: # Only top 3 to save tokens
            status = "✅ SUCCESS" if exp.get("outcome") == "SUCCESS" else "❌ FAILURE"
            formatted += f"- [{exp['timestamp']}] {status}: {exp.get('reasoning')} | Factors: {exp.get('factors')}\n"
        return formatted
