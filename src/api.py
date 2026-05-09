import logging
import time
import json
from typing import List, Optional
from cerebras.cloud.sdk import Cerebras
from .limiter import RateLimiter

logger = logging.getLogger("aiswarm.api")

class CerebrasClient:
    def __init__(self, api_key: str, limiter: RateLimiter, config_path: str = "config.json"):
        self.client = Cerebras(api_key=api_key)
        self.limiter = limiter
        with open(config_path, "r") as f:
            self.config = json.load(f)
        self.tiers = self.config.get("model_tiers", {})

    def call_with_retry(
        self, 
        messages: List[dict], 
        tier: str = "MEDIUM", 
        temperature: float = 0.7, 
        max_tokens: int = 2048
    ) -> Optional[str]:
        model = self.tiers.get(tier, "llama3.1-8b")
        max_retries = 3
        for attempt in range(max_retries):
            self.limiter.wait_if_needed()
            try:
                resp = self.client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_completion_tokens=max_tokens
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API Error: {e}")
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(1)
        return None
