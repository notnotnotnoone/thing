import os
import random
import time
import logging
from collections import deque
from typing import Any

logger = logging.getLogger("aiswarm.router.engine")

class SlidingWindow:
    def __init__(self, window_size: int = 65):
        self.window_size = window_size
        self.history = deque()  # list of (timestamp, tokens)

    def add(self, tokens: int):
        self.history.append((time.time(), tokens))

    def get_usage(self) -> tuple[int, int]:
        now = time.time()
        while self.history and now - self.history[0][0] > self.window_size:
            self.history.popleft()
        rpm = len(self.history)
        tpm = sum(h[1] for h in self.history)
        return rpm, tpm

class RoutingEngine:
    def __init__(self):
        self.model_windows: dict[str, SlidingWindow] = {}

    def get_best_provider(self, tier: str, providers: dict[str, Any]) -> tuple[str, str, str, str, str]:
        """
        Implements Capacity-First and Upgrade Fallback with per-model rate limiting.
        Returns (base_url, api_key, model_name, provider_name, final_tier)
        """
        tiers_order = ["SUPERLOW", "LOW", "MEDIUM", "HIGH", "EXTREME", "SYNTHESIS"]
        if tier not in tiers_order:
            logger.error(f"Invalid tier requested: {tier}")
            return "", "", "", "PAUSE", tier

        start_idx = tiers_order.index(tier)
        search_tiers = tiers_order[start_idx:]
        
        rejection_reasons = []

        for current_tier in search_tiers:
            candidates = []
            for p_name, p_data in providers.items():
                if current_tier not in p_data["models"]:
                    continue

                for model_cfg in p_data["models"][current_tier]:
                    model_name = model_cfg["name"]
                    rpm_limit_cfg = model_cfg["rpm"]
                    tpm_limit_cfg = model_cfg["tpm"]
                    
                    model_id = f"{p_name}:{model_name}"
                    if model_id not in self.model_windows:
                        self.model_windows[model_id] = SlidingWindow()

                    current_rpm, current_tpm = self.model_windows[model_id].get_usage()

                    # 10% safety pad, but ensure at least 1 request is possible if limit > 0
                    rpm_limit = max(0.1, rpm_limit_cfg * 0.9) if rpm_limit_cfg > 0 else 0
                    tpm_limit = max(1, tpm_limit_cfg * 0.9) if tpm_limit_cfg > 0 else 0
                    
                    # Detailed transparency logging for every check
                    status_msg = f"CHECK {model_id} | RPM: {current_rpm}/{rpm_limit_cfg} | TPM: {current_tpm}/{tpm_limit_cfg}"
                    
                    if rpm_limit_cfg == 0:
                        rejection_reasons.append(f"{model_id}: BLOCKED (0 Limit)")
                        logger.debug(f"{status_msg} -> REJECTED (Limit 0)")
                        continue
                    
                    if current_rpm >= rpm_limit:
                        rejection_reasons.append(f"{model_id}: RPM BUSY")
                        logger.debug(f"{status_msg} -> REJECTED (RPM Busy)")
                        continue
                        
                    if tpm_limit_cfg > 0 and current_tpm >= tpm_limit:
                        rejection_reasons.append(f"{model_id}: TPM BUSY")
                        logger.debug(f"{status_msg} -> REJECTED (TPM Busy)")
                        continue

                    # If we passed all checks
                    score = (rpm_limit - current_rpm) / rpm_limit if rpm_limit > 0 else 1.0
                    candidates.append((score, p_name, p_data, model_name, model_id))
                    logger.debug(f"{status_msg} -> CANDIDATE (Score: {score:.2f})")

            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_score = candidates[0][0]
                top_tier = [c for c in candidates if c[0] >= best_score * 0.8]
                _, p_name, p_data, model, model_id = random.choice(top_tier)

                keys = [k.strip() for k in os.environ.get(p_data["api_key_env"], "").split(",") if k.strip()]
                if not keys:
                    logger.warning(f"No API keys found in env {p_data['api_key_env']} for {p_name}")
                    rejection_reasons.append(f"{p_name}: NO API KEYS")
                    continue

                logger.info(f"Selected {model_id} for tier {tier} (via {current_tier})")
                return p_data["base_url"], random.choice(keys), model, p_name, current_tier

        # If no candidates found in any tier
        full_report = " | ".join(rejection_reasons[-5:]) # Show last 5 reasons
        logger.warning(f"Capacity Exhausted for {tier}. Reasons: {full_report}")
        return "", "", "", "PAUSE", tier

    def record_usage(self, provider_name: str, model_name: str, tokens: int):
        model_id = f"{provider_name}:{model_name}"
        if model_id not in self.model_windows:
            self.model_windows[model_id] = SlidingWindow()
        self.model_windows[model_id].add(tokens)
