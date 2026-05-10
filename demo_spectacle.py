import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Assuming these modules exist in your local src directory
from src.app.api import AsyncRouterClient
from src.app.router import ExtremeRouter
from src.app.ui import UI

async def demo_systems():
    ui = UI()
    
    # Prompt user for verbosity level
    ui.print_rule("DEMO STARTUP", "magenta")
    mode = ui.safe_input("Choose Mode: (1) NORMAL | (2) DEBUG/GLASS BOX")
    log_level = logging.DEBUG if mode == "2" else logging.INFO
    
    # Configure console logging based on user choice
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True # Override previous config
    )
    logger = logging.getLogger("SystemDiagnostic")

    # Ensure your config path is actually correct relative to where you run this
    router = ExtremeRouter("config/router.ini")
    client = AsyncRouterClient(router, ui)

    try:
        ui.print_banner("SYSTEM DIAGNOSTIC: THE MOVING SPECTACLE")

        # 0. INITIAL STATE
        ui.print_rule("PHASE 0: PRE-FLIGHT STATE", "dim")
        ui.display_system_state(router)

        # 1. PARALLEL SWARM BURST
        ui.print_rule("TEST 1: PARALLEL SWARM BURST", "cyan")
        ui.log_action("SYSTEM", "Firing 10 simultaneous requests across multiple tiers...")

        tiers = ["SUPERLOW", "LOW", "MEDIUM", "HIGH", "SUPERLOW", "LOW", "MEDIUM", "HIGH", "EXTREME", "SYNTHESIS"]
        
        tasks = []
        for i, tier in enumerate(tiers):
            prompt = [{"role": "user", "content": f"Test message {i}"}]
            # We wrap these in tasks to ensure they start immediately
            tasks.append(asyncio.create_task(client.call_with_retry(prompt, tier=tier, max_tokens=10)))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r and not isinstance(r, Exception))
        ui.log_action("SYSTEM", f"Burst complete. Successful responses: {success_count}/{len(tiers)}")
        
        # POST-BURST STATE
        ui.print_rule("PHASE 1.5: POST-BURST STATE", "dim")
        ui.display_system_state(router)

        # 2. ADVERSARIAL RECOVERY
        ui.print_rule("TEST 2: ADVERSARIAL RECOVERY", "red")
        ui.log_action("SYSTEM", "Simulating a 'Silent Failure' (empty response)...")

        # Reporting a manual failure to trigger the Penalty Box logic
        await router.report_result(
            provider="Cerebras",
            model="llama3.1-8b",
            tier="SUPERLOW",
            usage=None,
            status="silent_failure (manual demo)",
            content=""
        )

        ui.log_action("SYSTEM", "Cerebras penalized. Routing next request...")
        await client.call_with_retry([{"role": "user", "content": "Recovery test"}], tier="SUPERLOW", max_tokens=10)

        # 3. SYNTHESIS HARDENING
        ui.print_rule("TEST 3: SYNTHESIS HARDENING", "gold3")
        ui.log_action("SYSTEM", "Executing Masterpiece Synthesis...")
        await client.call_with_retry([{"role": "user", "content": "The final masterpiece"}], tier="SYNTHESIS", max_tokens=50)

        # 4. FINAL METRICS
        ui.print_rule("TEST 4: PERSISTENT AUDIT", "green")
        ui.log_action("METRICS", f"Total Session Cost: ${router.total_cost:.6f}")
        
        # 5. HOT-RELOAD PAUSE
        ui.console.print("\n[bold magenta]HOT-RELOAD DEMO:[/bold magenta]")
        ui.console.print("1. Change a rate_limit in 'router.ini'.")
        ui.console.print("2. Wait for the tick below.\n")

        await asyncio.sleep(10)
        # Triggering a model lookup usually forces the router to check file mtime
        await router.get_model("MEDIUM") 

    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
    finally:
        # If your router or client has close/cleanup methods, call them here
        ui.log_action("SYSTEM", "Cleaning up resources...")

if __name__ == "__main__":
    try:
        asyncio.run(demo_systems())
    except KeyboardInterrupt:
        print("\nUser aborted the spectacle.")
        sys.exit(0)