"""LLMAgent: ReAct-style tool-use merchant agent over the Merchant API Surface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from shopworld.agents.base import Agent
from shopworld.environment import Action, Observation

from llm_agent.client import LLMClient, ScriptedLLMClient
from llm_agent.react_loop import build_user_message, load_system_prompt, parse_action


class LLMAgent(Agent):
    name = "llm_agent"

    def __init__(self, client: Optional[LLMClient] = None, max_turns_per_ticket: int = 6):
        self.client: LLMClient = client or ScriptedLLMClient()
        self.system_prompt = load_system_prompt()
        self.max_turns_per_ticket = max_turns_per_ticket
        self._handled: set[str] = set()
        self._cur: Optional[Dict[str, Any]] = None
        self._history: List[str] = []
        self._turns = 0

    def reset(self, observation: Observation, info: Dict[str, Any]) -> None:
        self._handled = set()
        self._cur = None
        self._history = []
        self._turns = 0

    def act(self, observation: Observation) -> Optional[Action]:
        if self._cur is None:
            self._cur = self._next_ticket(observation)
            self._history = []
            self._turns = 0
            if self._cur is None:
                return None

        # Safety valve: don't loop forever on one ticket.
        if self._turns >= self.max_turns_per_ticket:
            self._finish_ticket()
            return self.act(observation)

        order = self._find_order(observation, self._cur.get("order_id"))
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": build_user_message(self._cur, order, self._history)},
        ]
        raw = self.client.complete(messages)
        decision = parse_action(raw)
        self._turns += 1

        if decision is None:  # unparseable -> give up on this ticket
            self._finish_ticket()
            return self.act(observation)

        tool = decision["tool"]
        args = decision.get("args", {})
        self._history.append(tool)
        if tool == "tickets.reply":  # reply closes out the ticket
            self._finish_ticket()
        return Action(tool, dict(args))

    # -- internals -----------------------------------------------------------

    def _finish_ticket(self) -> None:
        if self._cur is not None:
            self._handled.add(self._cur["id"])
        self._cur = None
        self._history = []
        self._turns = 0

    def _next_ticket(self, observation: Observation) -> Optional[Dict[str, Any]]:
        for ticket in observation.support_inbox.get("open_tickets", []):
            if ticket["id"] not in self._handled:
                return ticket
        return None

    def _find_order(self, observation: Observation, order_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not order_id:
            return None
        for order in observation.shopify_state.get("orders", []):
            if order.get("id") == order_id:
                return order
        return None
