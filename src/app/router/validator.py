import configparser
import logging
import os
from typing import Any

logger = logging.getLogger("aiswarm.router.validator")

class ConfigValidator:
    def __init__(self, ini_path: str):
        self.ini_path = ini_path
        self.last_mtime = 0.0

    def needs_reload(self) -> bool:
        try:
            mtime = os.path.getmtime(self.ini_path)
            if mtime > self.last_mtime:
                self.last_mtime = mtime
                return True
        except OSError:
            pass
        return False

    def validate_and_parse(self) -> dict[str, Any]:
        config = configparser.ConfigParser(interpolation=None)
        try:
            # Handle the multiline continuation manually or ensure configparser handles it
            config.read(self.ini_path)
            parsed = {}
            for section in config.sections():
                # Mandatory fields
                required = ["base_url", "api_key_env", "models"]
                for req in required:
                    if req not in config[section]:
                        raise ValueError(f"Missing required key '{req}' in section [{section}]")

                models = {}
                # Clean up the models string (remove backslashes and newlines)
                raw_models = config[section]["models"].replace("\\", "").replace("\n", "")
                
                for m_pair in raw_models.split(","):
                    parts = [p.strip() for p in m_pair.strip().split(":")]
                    if len(parts) < 2:
                        continue

                    name, tier = parts[0], parts[1]
                    # Support model_name:tier:rpm:tpm
                    rpm = float(parts[2]) if len(parts) > 2 else float(config[section].get("rate_limit", "30"))
                    tpm = int(parts[3]) if len(parts) > 3 else int(config[section].get("tpm_limit", "60000"))

                    if tier not in models:
                        models[tier] = []
                    models[tier].append({
                        "name": name, 
                        "rpm": rpm,
                        "tpm": tpm
                    })

                parsed[section] = {
                    "base_url": config[section]["base_url"],
                    "api_key_env": config[section]["api_key_env"],
                    "rate_limit": float(config[section].get("rate_limit", "30")),
                    "tpm_limit": int(config[section].get("tpm_limit", "60000")),
                    "models": models,
                    "price_prompt": float(config[section].get("price_prompt", "0.0")),
                    "price_completion": float(config[section].get("price_completion", "0.0"))
                }
            return parsed
        except Exception as e:
            logger.error(f"Config Validation Failed: {e}")
            raise
