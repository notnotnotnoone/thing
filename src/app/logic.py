import asyncio
import logging
import random
import re
import time

from rich.markdown import Markdown
from rich.panel import Panel

from .api import AsyncRouterClient
from .models import AgentMemory, Persona, Proposal
from .ui import UI

logger = logging.getLogger("aiswarm.logic")

class SwarmBrain:
    def __init__(self, client: AsyncRouterClient, ui: UI, core_personas: list[Persona], extra_personas: dict[str, list[Persona]]):
        self.client = client
        self.ui = ui
        self.core_personas = core_personas
        self.bookies = extra_personas.get("bookies", [])
        self.jesters = extra_personas.get("jesters", [])
        self.memories: dict[str, AgentMemory] = {}
        self.strategic_brief = ""
        self.news_flash = ""

    def _get_memory(self, agent_id: str) -> AgentMemory:
        if agent_id not in self.memories:
            self.memories[agent_id] = AgentMemory(agent_id=agent_id)
        return self.memories[agent_id]

    def _log_action(self, agent_id: str, action: str, content: str):
        memory = self._get_memory(agent_id)
        timestamp = time.strftime("%H:%M:%S")
        memory.past_actions.append({
            "time": timestamp, "action": action, "content": content
        })
        self.ui.log_action("Agent Logged", f"{agent_id} -> {action}")

    async def run_analyst_phase(self, user_prompt: str):
        self.ui.print_rule("PHASE 0: THE ANALYST", "green")
        with self.ui.console.status("[bold green]Analyst is scanning (EXTREME Tier)...[/]", spinner="arc"):
            prompt = f"Analyze this request and provide a high-level strategic briefing: {user_prompt}"
            response = await self.client.call_with_retry([{"role": "user", "content": prompt}], tier="EXTREME")
            self.strategic_brief = response or "Error generating brief."
        self.ui.console.print(Panel(self.strategic_brief, title="STRATEGIC BRIEFING", border_style="green"))

    async def generate_proposals(self, prompt: str) -> list[Proposal]:
        self.ui.print_rule("PHASE 1: THE GREAT BRAINSTORM (PARALLEL)", "cyan")

        async def agent_task(p: Persona):
            memory = self._get_memory(p.id)
            full_prompt = (
                f"Your Persona: {p.role}\n{p.description}\n"
                f"History: {memory.get_context_string()}\n"
                f"Brief: {self.strategic_brief}\nTask: {prompt}"
            )
            answer = await self.client.call_with_retry([{"role": "user", "content": full_prompt}], tier="MEDIUM")
            if answer:
                self.ui.display_proposal(p.id, p.role, answer, version=1)
                self._log_action(p.id, "drafted V1", answer[:50])
                return Proposal(id=p.id, role=p.role, answer_v1=answer)
            return None

        tasks = [agent_task(p) for p in self.core_personas]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]

    async def run_bookie(self, proposals: list[Proposal], stage: str = "Initial"):
        self.ui.print_rule(f"THE BOOKIE: {stage} Odds", "yellow")
        bookie = random.choice(self.bookies)
        summary = "\n".join([f"Agent {p.id} ({p.role}): V1 Length {len(p.answer_v1)}" for p in proposals])
        prompt = f"Persona: {bookie.role}\nStandings:\n{summary}\nSet odds for top 5 (e.g. A-01: 2/1)."
        response = await self.client.call_with_retry([{"role": "user", "content": prompt}], tier="SUPERLOW")
        if response:
            odds_map = {}
            matches = re.findall(r'([AWB]-\d+):\s*(\d+/\d+)', response)
            for aid, val in matches:
                odds_map[aid] = val
            self.ui.display_odds(bookie.role, odds_map, response)

    async def run_divine_intervention(self):
        self.ui.print_rule("PHASE 1.5: DIVINE INTERVENTION", "red")
        self.news_flash = self.ui.safe_input("ORACLE, DROP THE NEWS FLASH")
        if self.news_flash:
            self.ui.console.print(Panel(f"THE WORLD HAS CHANGED: {self.news_flash}", border_style="bold red"))

    async def run_jury_trials(self, proposals: list[Proposal]):
        self.ui.print_rule("PHASE 2: THE JURY (STAGGERED PARALLEL)", "magenta")

        async def trial_task(prop: Proposal):
            available_jurors = [p for p in self.core_personas if p.id != prop.id]
            selected_jury = random.sample(available_jurors, min(len(available_jurors), 3)) # Reduced for speed

            async def judge_task(juror: Persona):
                prompt = (
                    f"Persona: {juror.role}\nProposal: {prop.answer_v1}\n"
                    f"News: {self.news_flash}\nCritique & SCORE: X/10"
                )
                critique = await self.client.call_with_retry([{"role": "user", "content": prompt}], tier="LOW")
                if critique:
                    self.ui.display_critique(juror.id, juror.role, critique)
                    prop.jury_feedback.append(critique)
                    match = re.search(r'SCORE:\s*(\d+)', critique.upper())
                    score = int(match.group(1)) if match else 5
                    self._log_action(juror.id, f"judged {prop.id}", f"Score: {score}")

            # Parallelize jurors within a trial
            await asyncio.gather(*[judge_task(j) for j in selected_jury])

            # Jester Roast (Sequential to avoid too much noise)
            jester = random.choice(self.jesters)
            roast = await self.client.call_with_retry([{"role": "user", "content": f"Roast this: {prop.answer_v1}"}], tier="SUPERLOW")
            if roast:
                self.ui.display_critique(jester.id, jester.role, f"[bold red]ROAST:[/bold red] {roast}")

        # Staggered execution to not slam everything at once
        for i in range(0, len(proposals), 3):
            chunk = proposals[i:i+3]
            await asyncio.gather(*[trial_task(p) for p in chunk])

        return proposals

    async def run_refinement_phase(self, proposals: list[Proposal]):
        self.ui.print_rule("PHASE 3: SECOND CHANCE", "cyan")
        async def refine_task(prop: Proposal):
            p_persona = next(p for p in self.core_personas if p.id == prop.id)
            prompt = (
                f"Your Persona: {p_persona.role}\nNews: {self.news_flash}\n"
                f"V1: {prop.answer_v1}\nFeedback: {prop.jury_feedback}\nRefine to V2."
            )
            answer = await self.client.call_with_retry([{"role": "user", "content": prompt}], tier="MEDIUM")
            if answer:
                prop.answer_v2 = answer
                self.ui.display_proposal(prop.id, prop.role, answer, version=2)
                return prop
            return prop

        results = await asyncio.gather(*[refine_task(p) for p in proposals])
        return list(results)

    async def run_final_verdict(self, proposals: list[Proposal]):
        self.ui.print_rule("PHASE 4: FINAL VERDICT", "yellow")
        async def verdict_task(prop: Proposal):
            chief = random.choice(self.core_personas)
            prompt = f"Final Ruling on V2: {prop.answer_v2}\nSCORE: X/10"
            verdict = await self.client.call_with_retry([{"role": "user", "content": prompt}], tier="HIGH")
            if verdict:
                self.ui.display_verdict(chief.id, chief.role, verdict)
                match = re.search(r'SCORE:\s*(\d+)', verdict.upper())
                prop.score = int(match.group(1)) if match else 5
        await asyncio.gather(*[verdict_task(p) for p in proposals])
        return proposals

    async def run_synthesis_phase(self, proposals: list[Proposal]):
        self.ui.print_rule("PHASE 5: THE MASTERPIECE (SYNTHESIS Tier)", "gold3")
        sorted_props = sorted(proposals, key=lambda x: x.score, reverse=True)[:3]
        combined = "\n\n".join([f"Agent {p.id}: {p.answer_v2}" for p in sorted_props])
        prompt = f"Merge these top 3 into one Masterpiece:\n{combined}"
        synthesis = await self.client.call_with_retry([{"role": "user", "content": prompt}], tier="SYNTHESIS")
        if synthesis:
            self.ui.console.print(Panel(Markdown(synthesis), title="THE UNIFIED MASTERPIECE", border_style="gold3"))
            with open("masterpiece.md", "w") as f:
                f.write(synthesis)
