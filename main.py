import os
import json
import logging
from dotenv import load_dotenv
from src.models import Persona
from src.limiter import RateLimiter
from src.api import CerebrasClient
from src.ui import UI
from src.logic import SwarmBrain

# --- CONFIGURATION ---
load_dotenv()
CONFIG_FILE = "config.json"
PERSONAS_FILE = "personas.json"
EXTRA_PERSONAS_FILE = "extra_personas.json"
API_KEY = os.environ.get("CEREBRAS_API_KEY")

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("agent_history.log")]
)

def load_json(file_path: str) -> dict:
    with open(file_path, "r") as f:
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

def main():
    if not API_KEY:
        print("ERROR: CEREBRAS_API_KEY not found in environment.")
        exit(1)

    config = load_json(CONFIG_FILE)
    max_rpm = config.get("simulation", {}).get("max_rpm", 30)

    ui = UI()
    limiter = RateLimiter(max_rpm, "rate_limit.json")
    client = CerebrasClient(API_KEY, limiter, CONFIG_FILE)

    core_agents = load_personas(PERSONAS_FILE, "agent")
    extra_data = {
        "chatters": load_personas(EXTRA_PERSONAS_FILE, "chatter"),
        "bookies": load_personas(EXTRA_PERSONAS_FILE, "bookie"),
        "jesters": load_personas(EXTRA_PERSONAS_FILE, "jester")
    }

    brain = SwarmBrain(client, ui, core_agents, extra_data)

    ui.print_banner("FUNAITHINGS: THE UNSTABLE SPECTACLE")
    
    user_prompt = "How can we create a sustainable human colony on the surface of Venus?"
    
    try:
        brain.run_analyst_phase(user_prompt)
        proposals = brain.generate_proposals(user_prompt)
        
        brain.run_bookie(proposals, "Initial")
        brain.run_divine_intervention()
        brain.run_bookie(proposals, "Post-Crisis")
        
        proposals = brain.run_jury_trials(proposals)
        proposals = brain.run_refinement_phase(proposals)
        proposals = brain.run_final_verdict(proposals)
        
        brain.run_synthesis_phase(proposals)
        
        ui.display_leaderboard(proposals)
    except KeyboardInterrupt:
        print("\nShutdown requested by Oracle.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    main()
