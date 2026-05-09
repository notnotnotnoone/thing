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
        last_error = None
        
        for attempt in range(max_retries):
            self.limiter.wait_if_needed()
            try:
                logger.info(f"API Call (Attempt {attempt+1}/{max_retries}): Model={model}, Tier={tier}, Tokens={max_tokens}")
                resp = self.client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_completion_tokens=max_tokens
                )
                content = resp.choices[0].message.content.strip()
                logger.info(f"API Call Successful: Received {len(content)} characters")
                return content
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"API Error (Attempt {attempt+1}/{max_retries}): {error_type}: {error_msg}")
                
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if attempt == max_retries - 1:
                        logger.error(f"Final attempt failed. Raising exception.")
                        raise e
                    time.sleep(1)
        
        logger.error(f"All {max_retries} attempts failed. Last error: {last_error}")
        return None
