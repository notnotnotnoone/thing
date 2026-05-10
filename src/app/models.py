from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMemory:
    agent_id: str
    past_actions: list[dict[str, Any]] = field(default_factory=list)

    def get_context_string(self) -> str:
        if not self.past_actions:
            return "You have no history in this session yet."
        history = "Your previous actions/statements in this session:\n"
        for entry in self.past_actions:
            timestamp = entry.get("time", "N/A")
            action = entry.get("action", "said")
            content = entry.get("content", "")
            history += f"[{timestamp}] You {action}: {content}\n"
        return history

@dataclass
class Persona:
    id: str
    role: str
    description: str = ""
    type: str = "agent" # agent, chatter, bookie, jester

@dataclass
class Proposal:
    id: str
    role: str
    answer_v1: str = ""
    answer_v2: str = ""
    jury_feedback: list[str] = field(default_factory=list)
    jester_roast: str = ""
    score: int = 0
    judgments: list[str] = field(default_factory=list)
    duel_question: str = ""
    duel_answer: str = ""
