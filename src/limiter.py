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
        self.state = self._load_state()

    def _load_state(self) -> dict:
        default_state = {
            "requests": [],
            "last_reset": 0,
            "consecutive_failures": 0,
            "backoff_seconds": 1
        }
        try:
            if os.path.exists(self.limit_file):
                with open(self.limit_file, "r") as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**default_state, **loaded}
        except Exception as e:
            logger.warning(f"Could not load rate limit state from {self.limit_file}: {e}")
        return default_state

    def _save_state(self):
        try:
            with open(self.limit_file, "w") as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"Could not save rate limit state: {e}")

    def record_failure(self):
        """Record an API failure and increase backoff time exponentially."""
        with self.lock:
            self.state["consecutive_failures"] += 1
            # Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
            self.state["backoff_seconds"] = min(60, 2 ** (self.state["consecutive_failures"] - 1))
            self._save_state()
            logger.warning(f"Failure recorded. Consecutive failures: {self.state['consecutive_failures']}, Backoff: {self.state['backoff_seconds']}s")

    def record_success(self):
        """Record a successful API call and reset backoff."""
        with self.lock:
            self.state["consecutive_failures"] = 0
            self.state["backoff_seconds"] = 1
            self._save_state()

    def get_backoff_time(self) -> float:
        """Get current backoff time in seconds."""
        with self.lock:
            return self.state.get("backoff_seconds", 1)

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            # Clean old requests (older than 60 seconds)
            self.state["requests"] = [t for t in self.state["requests"] if now - t < 60]
            
            # Check if we've hit the RPM limit
            if len(self.state["requests"]) >= self.max_rpm:
                sleep_time = max(0, 60 - (now - self.state["requests"][0]) + 0.1)
                if sleep_time > 0:
                    logger.warning(f"Rate limit threshold reached. Cooling down for {sleep_time:.1f}s...")
                    # Release lock during sleep to allow other operations
                    self.lock.release()
                    try:
                        time.sleep(sleep_time)
                    finally:
                        self.lock.acquire()
                    now = time.time()
                    self.state["requests"] = [t for t in self.state["requests"] if now - t < 60]
            
            # Apply backoff if there were recent failures
            if self.state["consecutive_failures"] > 0:
                backoff = self.state["backoff_seconds"]
                logger.info(f"Applying exponential backoff: {backoff}s (failures: {self.state['consecutive_failures']})")
                self.lock.release()
                try:
                    time.sleep(backoff)
                finally:
                    self.lock.acquire()
            
            self.state["requests"].append(time.time())
            self.state["last_reset"] = now
            self._save_state()
