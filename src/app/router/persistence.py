import csv
import json
import os
import time
from typing import Any


class PersistenceManager:
    def __init__(self, audit_path: str = "session_audit.csv", health_path: str = "router_health.json"):
        self.audit_path = audit_path
        self.health_path = health_path
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.audit_path):
            with open(self.audit_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "provider", "model", "tier", "prompt_tokens", "completion_tokens", "cost", "status"])

    async def log_audit(self, provider: str, model: str, tier: str, p_tok: int, c_tok: int, cost: float, status: str):
        # Async-safe append
        row = [time.strftime("%Y-%m-%d %H:%M:%S"), provider, model, tier, p_tok, c_tok, f"{cost:.6f}", status]
        with open(self.audit_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    async def save_health(self, stats: dict[str, Any]):
        # Write to JSON atomically
        temp_path = self.health_path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(stats, f, indent=2)
        os.replace(temp_path, self.health_path)
