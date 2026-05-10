import logging
import time

logger = logging.getLogger("aiswarm.router.recovery")

class RecoveryManager:
    def __init__(self):
        self.penalty_box: dict[str, float] = {}  # provider -> timestamp until free
        self.consecutive_fails: dict[str, int] = {}

    def is_penalized(self, provider_name: str) -> bool:
        if provider_name in self.penalty_box:
            if time.time() < self.penalty_box[provider_name]:
                return True
            else:
                del self.penalty_box[provider_name]
        return False

    def report_failure(self, provider_name: str, error_type: str):
        self.consecutive_fails[provider_name] = self.consecutive_fails.get(provider_name, 0) + 1

        # Exponential penalty: 30s, 60s, 120s...
        delay = 30 * (2 ** (self.consecutive_fails[provider_name] - 1))
        delay = min(delay, 1800) # Max 30 mins
        self.penalty_box[provider_name] = time.time() + delay
        logger.warning(f"Provider {provider_name} penalized for {delay}s due to {error_type}")

    def report_success(self, provider_name: str):
        self.consecutive_fails[provider_name] = 0
        if provider_name in self.penalty_box:
            del self.penalty_box[provider_name]

    def semantic_validate(self, content: str) -> bool:
        """Adversarial check for 200 OK silent failures."""
        if not content or len(content.strip()) < 5:
            return False

        # Common "Refusal but 200 OK" patterns
        failures = [
            "i cannot fulfill", "as an ai language model",
            "service unavailable", "internal server error",
            "rate limit exceeded" # Sometimes leaked in body
        ]
        lower_content = content.lower()
        if any(f in lower_content for f in failures) and len(lower_content) < 150:
            return False

        return True
