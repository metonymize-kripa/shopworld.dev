"""Agent protocol and neutral baseline agents.

The benchmark runner is agent-blind: it depends only on this interface and never
imports a specific agent implementation. Both milli.run and the LLM agent satisfy
the same contract, which is how the runner guarantees interface equality
(README §13: "Both agents use identical Merchant API Surface").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from shopworld.environment import Action, Observation


class Agent(ABC):
    """Interface every evaluated merchant agent implements.

    Lifecycle per episode:
        agent.reset(observation, info)
        while not done:
            action = agent.act(observation)   # None => agent is finished
            observation, ... = env.step(action)
    """

    name: str = "agent"

    def reset(self, observation: Observation, info: Dict[str, Any]) -> None:
        """Prepare for a new episode. Override to clear per-episode memory."""

    @abstractmethod
    def act(self, observation: Observation) -> Optional[Action]:
        """Return the next action, or None to signal the agent is done."""
        raise NotImplementedError


class NoOpAgent(Agent):
    """Does nothing. Lower bound / smoke-test baseline."""

    name = "noop"

    def act(self, observation: Observation) -> Optional[Action]:
        return None


class BaselineAgent(Agent):
    """Minimal scripted support baseline (no NLU, no policy reasoning).

    For each open ticket it looks up the order, then posts one generic reply and
    stops. It deliberately ignores hidden state and policy, so it establishes a
    weak floor the real agents should beat. Vanilla-search analogue for the
    merchant track (README §9 baseline-relative scoring).
    """

    name = "baseline"

    def __init__(self) -> None:
        self._queue: list[str] = []
        self._handled: set[str] = set()
        self._phase = "lookup"

    def reset(self, observation: Observation, info: Dict[str, Any]) -> None:
        self._queue = []
        self._handled = set()
        self._phase = "lookup"

    def act(self, observation: Observation) -> Optional[Action]:
        open_tickets = observation.support_inbox.get("open_tickets", [])
        pending = [t for t in open_tickets if t["id"] not in self._handled]
        if not pending:
            return None

        ticket = pending[0]
        if self._phase == "lookup" and ticket.get("order_id"):
            self._phase = "reply"
            return Action("orders.query", {"id": ticket["order_id"]})

        self._phase = "lookup"
        self._handled.add(ticket["id"])
        return Action(
            "tickets.reply",
            {
                "ticket_id": ticket["id"],
                "body": "Thanks for reaching out — we're looking into this and will follow up.",
            },
        )
