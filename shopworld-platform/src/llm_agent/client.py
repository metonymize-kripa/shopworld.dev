"""LLM clients for the tool-use agent.

``LLMClient`` is the provider-agnostic interface. ``ScriptedLLMClient`` is a
deterministic offline stand-in that reads the structured context block the agent
embeds in each turn and returns a single JSON tool call — mimicking an LLM's
next-action decision so the benchmark runs without network access.
``AnthropicClient`` is a real adapter used when a model + API key are available.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Protocol

_INTENT_KEYWORDS = [
    ("CANCEL", ("cancel", "call off", "stop my order", "do not ship")),
    ("ADDRESS_CHANGE", ("address", "ship to", "moved", "deliver to")),
    ("REFUND", ("refund", "money back", "return my payment", "charged")),
    ("RETURN", ("return", "send back", "send this back", "does not fit")),
    ("WISMO", ("where is", "not arrived", "tracking", "late", "not received", "delivered")),
]

_CONTEXT_RE = re.compile(r"<CONTEXT>(.*?)</CONTEXT>", re.DOTALL)


def _keyword_intent(text: str) -> str:
    t = (text or "").lower()
    for label, kws in _INTENT_KEYWORDS:
        if any(k in t for k in kws):
            return label
    return "OTHER"


class LLMClient(Protocol):
    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Return one assistant turn: a JSON object describing the next action."""
        ...


class ScriptedLLMClient:
    """Deterministic offline LLM substitute.

    Competent tool-user, but unlike milli.run it has no hard policy guards, no
    confidence router, and no audit trail — it reasons from the visible order and
    relies on the tools to reject invalid actions. This makes the comparison
    empirical rather than rigged (README §9).
    """

    name = "scripted"

    def complete(self, messages: List[Dict[str, str]]) -> str:
        ctx = self._read_context(messages)
        return json.dumps(self._decide(ctx))

    def _read_context(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        for msg in reversed(messages):
            m = _CONTEXT_RE.search(msg.get("content", ""))
            if m:
                return json.loads(m.group(1))
        return {}

    def _decide(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        tid = ctx.get("ticket_id")
        oid = ctx.get("order_id")
        order = ctx.get("order") or {}
        status = order.get("display_fulfillment_status")
        history = ctx.get("history", [])
        intent = _keyword_intent(f"{ctx.get('subject','')} {ctx.get('description','')}")

        def reply(body: str) -> Dict[str, Any]:
            return {"tool": "tickets.reply", "args": {"ticket_id": tid, "body": body}}

        if intent == "WISMO":
            if "orders.query" not in history:
                return {"tool": "orders.query", "args": {"id": oid}}
            if "shipments.query" not in history:
                return {"tool": "shipments.query", "args": {"order_id": oid}}
            return reply("I checked your order and tracking — it's in transit and running late. We're on it.")

        if intent == "CANCEL":
            if "orders.query" not in history:
                return {"tool": "orders.query", "args": {"id": oid}}
            if status != "FULFILLED" and "orders.cancel" not in history:
                return {"tool": "orders.cancel", "args": {"order_id": oid, "reason": "customer"}}
            if status == "FULFILLED":
                return reply("Your order already shipped, so it can't be cancelled. You can return it once it arrives.")
            return reply("Your order has been cancelled and refunded.")

        if intent == "ADDRESS_CHANGE":
            if "orders.query" not in history:
                return {"tool": "orders.query", "args": {"id": oid}}
            if status not in ("FULFILLED", "PARTIAL") and "orders.update" not in history:
                return {"tool": "orders.update", "args": {"order_id": oid, "note": "Address change requested."}}
            return reply("I've updated your shipping address before the order ships.")

        if intent == "REFUND":
            if "orders.query" not in history:
                return {"tool": "orders.query", "args": {"id": oid}}
            if "refunds.create" not in history:
                amount = float(order.get("total_price", 0) or 0)
                return {"tool": "refunds.create", "args": {"order_id": oid, "amount": amount, "reason": "requested_by_customer"}}
            return reply("Your refund has been processed to your original payment method.")

        if intent == "RETURN":
            if "orders.query" not in history:
                return {"tool": "orders.query", "args": {"id": oid}}
            if "returns.create" not in history and status in ("FULFILLED", "PARTIAL"):
                return {"tool": "returns.create", "args": {"order_id": oid, "return_reason": "customer_request"}}
            return reply("I've started your return — a prepaid label is on its way by email.")

        return reply("Thanks for reaching out — I've noted your request and our team will follow up.")


class AnthropicClient:
    """Real LLM adapter (used when anthropic + ANTHROPIC_API_KEY are available).

    Not exercised in the offline test suite; provided so the agent architecture
    is genuinely model-backed. Falls back to raising if prerequisites are absent,
    which the benchmark entrypoint treats as "agent unavailable".
    """

    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 512):
        self.model = model
        self.max_tokens = max_tokens
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        try:
            import anthropic  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"anthropic SDK unavailable: {exc}")
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, messages: List[Dict[str, str]]) -> str:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": m["role"], "content": m["content"]} for m in convo],
        )
        return resp.content[0].text  # type: ignore[attr-defined]
