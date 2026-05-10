import asyncio
import logging

from openai import AsyncOpenAI

from .router import ExtremeRouter
from .ui import UI

logger = logging.getLogger("aiswarm.api")

class AsyncRouterClient:
    def __init__(self, router: ExtremeRouter, ui: UI):
        self.router = router
        self.ui = ui
        self.clients: dict[str, AsyncOpenAI] = {}

    def _get_client(self, base_url: str, api_key: str) -> AsyncOpenAI:
        cache_key = f"{base_url}_{api_key}"
        if cache_key not in self.clients:
            self.clients[cache_key] = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return self.clients[cache_key]

    async def call_with_retry(
        self,
        messages: list[dict],
        tier: str = "MEDIUM",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str | None:
        max_retries = 5

        for attempt in range(max_retries):
            # 1. Routing Decision
            base_url, api_key, model, p_name, final_tier = await self.router.get_model(tier)

            if p_name == "PAUSE":
                self.ui.log_action("CAPACITY EXHAUSTED", f"All providers for {tier} (and upgrades) are limited. Global Pause (60s)...")
                await asyncio.sleep(60)
                continue

            # 2. Synthesis Hardening (Handshake)
            if final_tier == "SYNTHESIS":
                self.ui.log_action("HANDSHAKE", f"Verifying {p_name} freshness for Masterpiece...")
                if not await self._perform_handshake(base_url, api_key, model, p_name):
                    self.ui.log_action("HANDSHAKE FAIL", f"{p_name} stale. Hopping...")
                    await self.router.report_result(p_name, model, final_tier, None, "handshake_fail")
                    continue

            # 3. Meta-Narrative Injection
            substrate_msg = f"\n\n[SYSTEM: HOST={p_name} | MODEL={model} | COST_SO_FAR={self.router.total_cost:.4f}]"
            modified_messages = []
            for m in messages:
                new_m = m.copy()
                if m["role"] == "system":
                    new_m["content"] += substrate_msg
                modified_messages.append(new_m)

            if not any(m["role"] == "system" for m in modified_messages):
                modified_messages.insert(0, {"role": "system", "content": f"You are an AI agent. {substrate_msg}"})

            # 4. Micro-Jitter
            await asyncio.sleep(0.1 + (attempt * 0.2))

            # 5. Execution
            self.ui.log_action("ASYNC ROUTE", f"Tier {tier} -> {p_name} ({model})")
            
            # GLASS BOX: Log exact payload being sent (DEBUG ONLY)
            if logger.isEnabledFor(logging.DEBUG):
                self.ui.log_payload(f"REQUEST TO {p_name}", {
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": modified_messages
                })
            
            client = self._get_client(base_url, api_key)

            try:
                resp = await client.chat.completions.create(
                    messages=modified_messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=60.0 # Circuit breaker timeout
                )
                
                # Enhanced transparency logging
                content = resp.choices[0].message.content
                if content is not None:
                    content = content.strip()
                usage = resp.usage
                
                self.ui.log_action("ASYNC OK", f"{p_name} ({model}) | Status: 200 OK | Usage: P={usage.prompt_tokens}, C={usage.completion_tokens}")

                # GLASS BOX: Log exact response content (DEBUG ONLY)
                if logger.isEnabledFor(logging.DEBUG):
                    self.ui.log_payload(f"RESPONSE FROM {p_name}", {
                        "status": "200 OK",
                        "usage": {
                            "prompt": usage.prompt_tokens,
                            "completion": usage.completion_tokens,
                            "total": usage.total_tokens
                        },
                        "content": content
                    })

                # 6. Usage Reporting & Semantic Validation
                await self.router.report_result(p_name, model, final_tier, usage, "success", content)

                # If the router marked it as a silent failure, content might be invalid
                # but we return it anyway and let the logic layer handle it or the next retry
                if not content or "silent_failure" in str(usage): # Usage won't have it, router logic does
                    continue

                return content

            except Exception as e:
                self.ui.log_action("ASYNC ERROR", f"{p_name}: {str(e)[:50]}...")
                await self.router.report_result(p_name, model, final_tier, None, f"exception: {str(e)[:100]}")
                
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(1)

        return None

    async def _perform_handshake(self, base_url: str, api_key: str, model: str, provider: str) -> bool:
        """1-token pre-flight check."""
        client = self._get_client(base_url, api_key)
        try:
            await client.chat.completions.create(
                messages=[{"role": "user", "content": "hi"}],
                model=model,
                max_tokens=1,
                timeout=5.0
            )
            return True
        except Exception:
            return False
