import asyncio
import logging
from typing import Any

from .engine import RoutingEngine
from .persistence import PersistenceManager
from .recovery import RecoveryManager
from .validator import ConfigValidator

logger = logging.getLogger("aiswarm.router")

class ExtremeRouter:
    def __init__(self, ini_path: str = "router.ini"):
        self.validator = ConfigValidator(ini_path)
        self.engine = RoutingEngine()
        self.recovery = RecoveryManager()
        self.persistence = PersistenceManager()
        self.providers: dict[str, Any] = {}
        self.total_cost = 0.0
        self.lock = asyncio.Lock()

        # Initial load
        self.providers = self.validator.validate_and_parse()

    async def get_model(self, tier: str) -> tuple[str, str, str, str, str]:
        async with self.lock:
            if self.validator.needs_reload():
                logger.info("Hot-reloading router configuration...")
                self.providers = self.validator.validate_and_parse()

            # Filter out penalized providers before passing to engine
            active_providers = {
                name: data for name, data in self.providers.items()
                if not self.recovery.is_penalized(name)
            }

            return self.engine.get_best_provider(tier, active_providers)

    async def report_result(self, provider: str, model: str, tier: str, usage: Any, status: str, content: str = ""):
        async with self.lock:
            # Semantic Validation
            if status == "success" and not self.recovery.semantic_validate(content):
                status = "silent_failure (empty/refusal)"
                self.recovery.report_failure(provider, status)
            elif status == "success":
                self.recovery.report_success(provider)
                p_tok = usage.prompt_tokens
                c_tok = usage.completion_tokens
                self.engine.record_usage(provider, model, p_tok + c_tok)

                # Cost Calculation
                p_data = self.providers.get(provider, {})
                cost = (p_tok / 1000 * p_data.get("price_prompt", 0)) + \
                       (c_tok / 1000 * p_data.get("price_completion", 0))
                self.total_cost += cost

                await self.persistence.log_audit(provider, model, tier, p_tok, c_tok, cost, "success")
            else:
                self.recovery.report_failure(provider, status)
                await self.persistence.log_audit(provider, model, tier, 0, 0, 0.0, status)

            await self._update_health_file()
    async def _update_health_file(self):
        stats = {
            "total_cost": f"${self.total_cost:.4f}",
            "providers": {}
        }
        for model_id, window in self.engine.model_windows.items():
            rpm, _ = window.get_usage()
            stats["providers"][model_id] = {
                "usage": f"{rpm} RPM"
            }
        await self.persistence.save_health(stats)

    async def handshake(self, provider_name: str, model_name: str, tier: str) -> bool:
        """Synthesis tier hardening handshake logic would be called from API client."""
        # This is a stub for the API client to call a 1-token check
        return True
