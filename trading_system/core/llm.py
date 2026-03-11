"""
llm.py -- OpenRouter and LLM Integration for APEX Trading System
"""
import os
import json
import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger("apex.core.llm")

class APEXLLM:
    """
    Unified interface for LLM calls with OpenRouter support.
    Configured to use free/low-cost models by default.
    """
    
    def __init__(self, config=None):
        from .config import APEXConfig
        self.config = config or APEXConfig()
        self.api_key = self.config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = self.config.OPENROUTER_MODEL or "google/gemini-2.0-flash-lite-preview-02-05:free"

    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        Send a chat completion request to OpenRouter.
        """
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not found in configuration.")
            return None

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/sn-sujay/apex-trading-system",
            "X-Title": "APEX Trading System",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            return None

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Specific helper for news or social sentiment analysis.
        """
        prompt = [
            {"role": "system", "content": "You are a senior financial analyst. Analyze the sentiment of the following news headline/text for its impact on the Indian stock market (NIFTY 50). Respond ONLY in JSON: {\"sentiment\": \"BULLISH\"|\"BEARISH\"|\"NEUTRAL\", \"confidence\": 0.0-1.0, \"impact_score\": -100 to 100, \"reasoning\": \"string\"}"},
            {"role": "user", "content": text}
        ]
        
        response = await self.chat_completion(prompt)
        if not response:
            return {"sentiment": "NEUTRAL", "confidence": 0.0, "reasoning": "LLM call failed"}
        
        try:
            cleaned = response.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return {"sentiment": "NEUTRAL", "confidence": 0.0, "reasoning": "JSON parse error"}

    async def analyze_with_memory(self, agent_name: str, context: str, memory_str: str) -> Dict[str, Any]:
        """
        Analyze a situation while considering long-term 'Lessons Learned'.
        Inspired by Hermes/Autoresearch patterns.
        """
        prompt = [
            {"role": "system", "content": f"You are the {agent_name} for APEX. Your goal is to provide a directional bias based on available data and PAST LESSONS. \n\n{memory_str}\n\nAssess the current situation against these past outcomes. If a previous similar setup failed, be extremely cautious. Respond ONLY in JSON: {{\"direction\": \"BULLISH\"|\"BEARISH\"|\"NEUTRAL\", \"confidence\": 0.0-1.0, \"reasoning\": \"string\", \"key_factors\": []}}"},
            {"role": "user", "content": f"CURRENT SITUATION: {context}"}
        ]
        
        response = await self.chat_completion(prompt)
        if not response:
            return {"direction": "NEUTRAL", "confidence": 0.0, "reasoning": "Memory-LLM call failed"}
            
        try:
            cleaned = response.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned)
        except Exception:
            return {"direction": "NEUTRAL", "confidence": 0.0, "reasoning": "JSON error"}

# Singleton instance
_llm_instance = None

def get_llm(config=None):
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = APEXLLM(config)
    return _llm_instance
