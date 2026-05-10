import asyncio
import json
import logging

from dotenv import load_dotenv

from src.app.api import AsyncRouterClient
from src.app.logic import SwarmBrain
from src.app.models import Persona
from src.app.router import ExtremeRouter
from src.app.ui import UI

# --- CONFIGURATION ---
load_dotenv()
INI_FILE = "config/router.ini"
PERSONAS_FILE = "config/personas.json"
EXTRA_PERSONAS_FILE = "config/extra_personas.json"

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("agent_history.log")]
)

def load_json(file_path: str) -> dict:
    with open(file_path) as f:
        return json.load(f)

def load_personas(file_path: str, p_type: str = "agent") -> list:
    try:
        data = load_json(file_path)
        if "swarm_config" in data:
            agents_data = data["swarm_config"].get("agents", [])
        elif p_type + "s" in data:
            agents_data = data[p_type + "s"]
        else:
            agents_data = []

        personas = []
        for a in agents_data:
            filtered_data = {k: v for k, v in a.items() if k in ["id", "role", "description"]}
            personas.append(Persona(type=p_type, **filtered_data))
        return personas
    except Exception as e:
        logging.error(f"Failed to load {p_type} personas from {file_path}: {e}")
        return []

async def async_main():
    ui = UI()

    try:
        router = ExtremeRouter(INI_FILE)
        client = AsyncRouterClient(router, ui)
    except Exception as e:
        ui.log_action("FATAL CONFIG ERROR", str(e))
        ui.console.print(f"[bold red]Please fix {INI_FILE} and restart.[/]")
        return

    core_agents = load_personas(PERSONAS_FILE, "agent")
    extra_data = {
        "chatters": load_personas(EXTRA_PERSONAS_FILE, "chatter"),
        "bookies": load_personas(EXTRA_PERSONAS_FILE, "bookie"),
        "jesters": load_personas(EXTRA_PERSONAS_FILE, "jester")
    }

    brain = SwarmBrain(client, ui, core_agents, extra_data)

    ui.print_banner("THE UNSTABLE SPECTACLE: EXTREME-EFFORT ASYNC ENGINE")

    user_prompt = "How can we create a sustainable human colony on the surface of Venus?"

    try:
        await brain.run_analyst_phase(user_prompt)
        proposals = await brain.generate_proposals(user_prompt)

        await brain.run_bookie(proposals, "Initial")
        await brain.run_divine_intervention()
        await brain.run_bookie(proposals, "Post-Crisis")

        proposals = await brain.run_jury_trials(proposals)
        proposals = await brain.run_refinement_phase(proposals)
        proposals = await brain.run_final_verdict(proposals)

        await brain.run_synthesis_phase(proposals)

        ui.display_leaderboard(proposals)
    except KeyboardInterrupt:
        print("\nShutdown requested by Oracle.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        ui.console.print(f"[bold red]FATAL ERROR: {e}[/]")

if __name__ == "__main__":
    asyncio.run(async_main())
