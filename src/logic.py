import random
import re
import logging
import time
from typing import List, Dict, Any, Optional
from rich.panel import Panel
from rich.markdown import Markdown
from .models import Persona, Proposal, AgentMemory
from .api import CerebrasClient
from .ui import UI

logger = logging.getLogger("aiswarm.logic")
evolution_logger = logging.getLogger("evolution")

class SwarmBrain:
    def __init__(self, client: CerebrasClient, ui: UI, core_personas: List[Persona], extra_personas: Dict[str, List[Persona]]):
        self.client = client
        self.ui = ui
        self.core_personas = core_personas
        self.bookies = extra_personas.get("bookies", [])
        self.jesters = extra_personas.get("jesters", [])
        self.memories: Dict[str, AgentMemory] = {}
        self.strategic_brief = ""
        self.news_flash = ""
        self.ui.log_action("SwarmBrain initialized", f"{len(core_personas)} core agents loaded.")

    def _get_memory(self, agent_id: str) -> AgentMemory:
        if agent_id not in self.memories:
            self.ui.log_action("Memory Allocation", f"Creating new memory buffer for {agent_id}")
            self.memories[agent_id] = AgentMemory(agent_id=agent_id)
        return self.memories[agent_id]

    def _log_action(self, agent_id: str, action: str, content: str):
        memory = self._get_memory(agent_id)
        timestamp = time.strftime("%H:%M:%S")
        memory.past_actions.append({
            "time": timestamp,
            "action": action,
            "content": content
        })
        self.ui.log_action(f"Agent Action Logged", f"{agent_id} performed '{action}' at {timestamp}")

    def run_analyst_phase(self, user_prompt: str):
        self.ui.print_rule("PHASE 0: THE ANALYST", "green")
        tier = self.client.config.get("default_tiers", {}).get("analyst", "EXTREME")
        
        with self.ui.console.status(f"[bold green]Analyst is scanning the landscape (Tier: {tier})...[/]", spinner="arc"):
            self.ui.log_action("Preprocessing", f"Sending prompt to {tier} model...")
            prompt = f"Analyze this request and provide a high-level strategic briefing for a swarm of 30 specialized AI agents: {user_prompt}"
            response = self.client.call_with_retry([{"role": "user", "content": prompt}], tier=tier)
            self.strategic_brief = response if response else "Error generating strategic brief."
        
        self.ui.log_action("Context Injected", "Strategic briefing has been broadcast to all agents.")
        self.ui.console.print(Panel(self.strategic_brief, title="STRATEGIC BRIEFING", border_style="green"))

    def generate_proposals(self, prompt: str) -> List[Proposal]:
        self.ui.print_rule("PHASE 1: THE GREAT BRAINSTORM", "cyan")
        proposals = []
        tier = self.client.config.get("default_tiers", {}).get("brainstorm", "MEDIUM")
        
        for p in self.core_personas:
            self.ui.log_action("Tasking Agent", f"Invoking {p.id} ({p.role})")
            memory = self._get_memory(p.id)
            context = memory.get_context_string()
            
            with self.ui.console.status(f"[bold cyan]Agent {p.id} is thinking (Tier: {tier})...[/]", spinner="dots"):
                self.ui.log_action("Context Construction", f"Injecting {len(context)} bytes of history...")
                full_prompt = (
                    f"Your Persona: {p.role}\n{p.description}\n"
                    f"Session History: {context}\n"
                    f"Strategic Briefing: {self.strategic_brief}\n"
                    f"Task: {prompt}\n"
                    "Write a detailed proposal. Focus on your expertise."
                )
                answer = self.client.call_with_retry([{"role": "user", "content": full_prompt}], tier=tier)
            
            if answer:
                self.ui.display_proposal(p.id, p.role, answer, version=1)
                self._log_action(p.id, "drafted V1 proposal", answer[:100] + "...")
                proposals.append(Proposal(id=p.id, role=p.role, answer_v1=answer))
            else:
                self.ui.log_action("Execution Failure", f"Agent {p.id} failed to respond.")
        return proposals

    def run_bookie(self, proposals: List[Proposal], stage: str = "Initial"):
        self.ui.print_rule(f"THE BOOKIE: {stage} Odds", "yellow")
        tier = self.client.config.get("default_tiers", {}).get("spectacle", "SUPERLOW")
        bookie = random.choice(self.bookies)
        
        with self.ui.console.status(f"[bold yellow]Bookie {bookie.id} is calculating the spread...[/]", spinner="money"):
            self.ui.log_action("Probability Math", f"Aggregating {len(proposals)} proposals for comparison...")
            summary = "\n".join([f"Agent {p.id} ({p.role}): V1 Length {len(p.answer_v1)} chars" for p in proposals])
            prompt = (
                f"Persona: {bookie.role} - {bookie.description}\n"
                f"Current Standings:\n{summary}\n"
                f"Strategic Brief: {self.strategic_brief}\n"
                "As a professional bookie, set betting odds for the top 5 agents. Format as 'Agent ID: Odds' (e.g. A-01: 2/1). Be snappy."
            )
            response = self.client.call_with_retry([{"role": "user", "content": prompt}], tier=tier)
            
            if response:
                self.ui.log_action("Parsing Odds", "Extracting Agent-to-Value mappings...")
                odds_map = {}
                matches = re.findall(r'([AWB]-\d+):\s*(\d+/\d+)', response)
                for aid, val in matches:
                    odds_map[aid] = val
                
                self.ui.display_odds(bookie.role, odds_map, response)
                self._log_action(bookie.id, f"calculated {stage} odds", response[:100])
        return

    def run_divine_intervention(self):
        self.ui.print_rule("PHASE 1.5: DIVINE INTERVENTION", "red")
        self.ui.log_action("Simulation Paused", "Waiting for Oracle input...")
        self.news_flash = self.ui.safe_input("ORACLE, DROP THE NEWS FLASH (Leave blank for no change)")
        
        if self.news_flash:
            self.ui.log_action("Reality Altered", f"Broadcasting News Flash: {self.news_flash}")
            self.ui.console.print(Panel(f"THE WORLD HAS CHANGED: {self.news_flash}", title="NEWS FLASH", border_style="bold red"))
        else:
            self.ui.log_action("Simulation Resumed", "No world changes detected.")

    def run_jury_trials(self, proposals: List[Proposal]):
        self.ui.print_rule("PHASE 2: THE JURY", "magenta")
        critique_tier = self.client.config.get("default_tiers", {}).get("critique", "LOW")
        spectacle_tier = self.client.config.get("default_tiers", {}).get("spectacle", "SUPERLOW")
        
        for idx, prop in enumerate(proposals):
            self.ui.print_rule(f"TRIAL {idx+1}/{len(proposals)}: {prop.id}", "white")
            self.ui.log_action("Trial Commenced", f"Empaneling jury for {prop.id}")
            
            available_jurors = [p for p in self.core_personas if p.id != prop.id]
            selected_jury = random.sample(available_jurors, min(len(available_jurors), 6))
            
            for juror in selected_jury:
                memory = self._get_memory(juror.id)
                with self.ui.console.status(f"[bold magenta]Juror {juror.id} is critiquing (Tier: {critique_tier})...[/]", spinner="bouncingBar"):
                    self.ui.log_action("Judgment Call", f"Juror {juror.id} is reviewing {prop.id}'s proposal...")
                    judge_prompt = (
                        f"Persona: {juror.role}\n{memory.get_context_string()}\n"
                        f"Proposal to Judge: {prop.answer_v1}\n"
                        f"News Flash: {self.news_flash}\n"
                        "Critique this proposal. Be honest and specific. End with SCORE: X/10"
                    )
                    critique = self.client.call_with_retry([{"role": "user", "content": judge_prompt}], tier=critique_tier)
                    if critique:
                        self.ui.display_critique(juror.id, juror.role, critique)
                        prop.jury_feedback.append(critique)
                        match = re.search(r'SCORE:\s*(\d+)', critique.upper())
                        score = int(match.group(1)) if match else 5
                        self._log_action(juror.id, f"judged {prop.id}", f"Score: {score}")

            # Jester Roast
            jester = random.choice(self.jesters)
            with self.ui.console.status(f"[bold red]Jester {jester.id} is roasting...[/]", spinner="aesthetic"):
                self.ui.log_action("Chaos Injection", f"Jester {jester.id} providing mandatory roast.")
                j_prompt = f"Jester Persona: {jester.role}\nProposal: {prop.answer_v1}\nRoast this proposal brutally."
                roast = self.client.call_with_retry([{"role": "user", "content": j_prompt}], tier=spectacle_tier)
                if roast:
                    prop.jester_roast = roast
                    self.ui.display_critique(jester.id, jester.role, f"[bold red]ROAST:[/bold red] {roast}")
        return proposals

    def run_refinement_phase(self, proposals: List[Proposal]):
        self.ui.print_rule("PHASE 3: SECOND CHANCE", "cyan")
        tier = self.client.config.get("default_tiers", {}).get("brainstorm", "MEDIUM")
        
        for prop in proposals:
            p_persona = next(p for p in self.core_personas if p.id == prop.id)
            memory = self._get_memory(prop.id)
            feedback_str = "\n".join([f"- {f[:200]}..." for f in prop.jury_feedback])
            
            with self.ui.console.status(f"[bold cyan]Agent {prop.id} is refining proposal (V2)...[/]", spinner="growVertical"):
                self.ui.log_action("Feedback Synthesis", f"Agent {prop.id} is processing jury notes...")
                prompt = (
                    f"Your Persona: {p_persona.role}\n{memory.get_context_string()}\n"
                    f"News Flash: {self.news_flash}\n"
                    f"Your V1 Draft: {prop.answer_v1}\n"
                    f"Jury Feedback: {feedback_str}\n"
                    "This is your SECOND CHANCE. Rewrite your proposal to address the feedback and the News Flash."
                )
                answer = self.client.call_with_retry([{"role": "user", "content": prompt}], tier=tier)
            
            if answer:
                prop.answer_v2 = answer
                self.ui.display_proposal(prop.id, prop.role, answer, version=2)
                self._log_action(prop.id, "refined proposal to V2", answer[:100] + "...")
        return proposals

    def run_final_verdict(self, proposals: List[Proposal]):
        self.ui.print_rule("PHASE 4: FINAL VERDICT", "yellow")
        tier = self.client.config.get("default_tiers", {}).get("verdict", "HIGH")
        
        for prop in proposals:
            chief = random.choice(self.core_personas)
            with self.ui.console.status(f"[bold yellow]Chief Justice {chief.id} is rendering verdict...[/]", spinner="dqpb"):
                self.ui.log_action("Supreme Judgment", f"Chief Justice {chief.id} is reviewing V2 of {prop.id}")
                prompt = (
                    f"Chief Justice Persona: {chief.role}\n"
                    f"Proposal (V2): {prop.answer_v2}\n"
                    f"News Flash: {self.news_flash}\n"
                    "Provide a final ruling and end with SCORE: X/10"
                )
                verdict = self.client.call_with_retry([{"role": "user", "content": prompt}], tier=tier)
                if verdict:
                    self.ui.log_action("Score Extraction", f"Parsing final score for {prop.id}...")
                    self.ui.display_verdict(chief.id, chief.role, verdict)
                    match = re.search(r'SCORE:\s*(\d+)', verdict.upper())
                    prop.score = int(match.group(1)) if match else 5
        return proposals

    def run_synthesis_phase(self, proposals: List[Proposal]):
        self.ui.print_rule("PHASE 5: THE MASTERPIECE", "gold3")
        tier = self.client.config.get("default_tiers", {}).get("synthesis", "EXTREME")
        sorted_props = sorted(proposals, key=lambda x: x.score, reverse=True)[:3]
        
        with self.ui.console.status(f"[bold gold3]Synthesizer is merging champions (Tier: {tier})...[/]", spinner="moon"):
            self.ui.log_action("Deep Integration", f"Merging Top 3 strategies ({[p.id for p in sorted_props]})")
            combined = "\n\n".join([f"Agent {p.id} Strategy: {p.answer_v2}" for p in sorted_props])
            prompt = f"Merge these 3 top-tier AI proposals into one unified, ultimate strategy document:\n{combined}"
            synthesis = self.client.call_with_retry([{"role": "user", "content": prompt}], tier=tier)
        
        if synthesis:
            self.ui.log_action("Masterpiece Generated", "Saving final document to masterpiece.md")
            self.ui.console.print(Panel(Markdown(synthesis), title="THE UNIFIED MASTERPIECE", border_style="gold3"))
            with open("masterpiece.md", "w") as f:
                f.write(synthesis)
        return
