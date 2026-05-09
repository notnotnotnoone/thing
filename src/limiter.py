import time
import json
import os
import logging
import threading
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

logger = logging.getLogger("aiswarm.limiter")

class RateLimiter:
    def __init__(self, max_rpm: int, limit_file: str):
        self.max_rpm = max_rpm
        self.limit_file = limit_file
        self.lock = threading.Lock()
        self.history = self._load_history()

    def _load_history(self) -> list:
        try:
            if os.path.exists(self.limit_file):
                with open(self.limit_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self):
        try:
            with open(self.limit_file, "w") as f:
                json.dump(self.history, f)
        except Exception:
            pass

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            self.history = [t for t in self.history if now - t < 60]
            if len(self.history) >= self.max_rpm:
                sleep_time = max(0, 60 - (now - self.history[0]) + 0.1)
                if sleep_time > 0:
                    logger.warning(f"Rate limit threshold reached. Cooling down for {sleep_time:.1f}s...")
                    # We sleep inside the lock to block other threads from hitting the limit
                    time.sleep(sleep_time)
                    now = time.time()
                    self.history = [t for t in self.history if now - t < 60]
            
            self.history.append(time.time())
            self._save_history()
