import logging
import time
import json
from typing import List, Optional
from cerebras.cloud.sdk import Cerebras, AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError, InternalServerError
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
        max_retries = 5
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
                
                # Record success to reset backoff
                self.limiter.record_success()
                return content
                
            except RateLimitError as e:
                last_error = e
                error_code = getattr(e, 'status_code', 'Unknown')
                error_msg = str(e)
                logger.error(f"RATE LIMIT ERROR (Attempt {attempt+1}/{max_retries}): [{error_code}] {error_msg}")
                
                # Record failure for exponential backoff
                self.limiter.record_failure()
                
                # Calculate wait time based on consecutive failures
                base_wait = self.limiter.get_backoff_time()
                # Add additional time for 429 errors specifically
                wait_time = max(base_wait, (attempt + 1) * 5)
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry (exponential backoff active)...")
                time.sleep(wait_time)
                
            except AuthenticationError as e:
                # Auth errors should not be retried - they will never succeed
                last_error = e
                error_msg = f"AuthenticationError: {str(e)}"
                logger.critical(f"AUTHENTICATION FAILED: {error_msg}")
                print(f"\n[bold red]╔═══════════════════════════════════════════════════════════╗[/bold red]")
                print(f"[bold red]║ CRITICAL: AUTHENTICATION ERROR                              ║[/bold red]")
                print(f"[bold red]╠═══════════════════════════════════════════════════════════╣[/bold red]")
                print(f"[red]{error_msg}[/red]")
                print(f"[bold red]╚═══════════════════════════════════════════════════════════╝[/bold red]\n")
                raise e  # Re-raise to stop execution
                
            except APIConnectionError as e:
                last_error = e
                error_msg = f"APIConnectionError: {str(e)}"
                logger.error(f"CONNECTION ERROR (Attempt {attempt+1}/{max_retries}): {error_msg}")
                self.limiter.record_failure()
                wait_time = self.limiter.get_backoff_time()
                logger.warning(f"Connection issue. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                
            except APITimeoutError as e:
                last_error = e
                error_msg = f"APITimeoutError: {str(e)}"
                logger.error(f"TIMEOUT ERROR (Attempt {attempt+1}/{max_retries}): {error_msg}")
                self.limiter.record_failure()
                wait_time = self.limiter.get_backoff_time() * 2  # Timeouts need longer waits
                logger.warning(f"Request timed out. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                
            except InternalServerError as e:
                last_error = e
                error_code = getattr(e, 'status_code', '500')
                error_msg = f"InternalServerError [{error_code}]: {str(e)}"
                logger.error(f"SERVER ERROR (Attempt {attempt+1}/{max_retries}): {error_msg}")
                self.limiter.record_failure()
                wait_time = self.limiter.get_backoff_time()
                logger.warning(f"Server error. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"UNEXPECTED ERROR (Attempt {attempt+1}/{max_retries}): {error_type}: {error_msg}")
                self.limiter.record_failure()
                
                # Always apply backoff for any error
                wait_time = self.limiter.get_backoff_time()
                
                if attempt == max_retries - 1:
                    # Final attempt failed - show detailed error
                    logger.critical(f"All {max_retries} attempts failed. Last error: {error_type}: {error_msg}")
                    print(f"\n[bold red]╔═══════════════════════════════════════════════════════════╗[/bold red]")
                    print(f"[bold red]║ CRITICAL ERROR AFTER {max_retries} RETRIES                            ║[/bold red]")
                    print(f"[bold red]╠═══════════════════════════════════════════════════════════╣[/bold red]")
                    print(f"[red]Error Type: {error_type}[/red]")
                    print(f"[red]Error Message: {error_msg}[/red]")
                    print(f"[red]Model: {model}, Tier: {tier}[/red]")
                    print(f"[bold red]╚═══════════════════════════════════════════════════════════╝[/bold red]\n")
                    raise e  # Re-raise so caller knows it failed
                else:
                    logger.warning(f"Waiting {wait_time}s before next retry...")
                    time.sleep(wait_time)
        
        # Should never reach here, but just in case
        logger.error(f"All retries exhausted. Final error: {last_error}")
        raise last_error
