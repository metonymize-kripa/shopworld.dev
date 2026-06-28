"""LLM clients for the tool-use agent.

``LLMClient`` is the provider-agnostic interface. ``ScriptedLLMClient`` is a
deterministic offline stand-in that reads the structured context block the agent
embeds in each turn and returns a single JSON tool call — mimicking an LLM's
next-action decision so the benchmark runs without network access.
``AnthropicClient`` is a real adapter used when a model + API key are available.
``OllamaClient`` is a local-model adapter used when an Ollama server is running.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
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


class OllamaClient:
    """Local LLM adapter for an Ollama chat model.

    Uses Ollama's HTTP API directly so the benchmark does not need an extra
    Python package. The benchmark entrypoint treats constructor failures as
    "agent unavailable" and skips cleanly when Ollama is not running or the
    requested model is not pulled.
    """

    name = "ollama"

    def __init__(
        self,
        model: str = "gemma4:12b-mlx",
        base_url: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = (base_url or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._validate_model_available()

    def complete(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        data = self._post_json("/api/chat", payload)
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"unexpected Ollama response shape: {data!r}")
        return content

    def _validate_model_available(self) -> None:
        data = self._get_json("/api/tags")
        names = {model.get("name") for model in data.get("models", []) if isinstance(model, dict)}
        if self.model not in names:
            available = ", ".join(sorted(str(name) for name in names if name)) or "none"
            raise RuntimeError(
                f"Ollama model {self.model!r} is not available at {self.base_url}; "
                f"available models: {available}. Run `ollama pull {self.model}` or set SHOPWORLD_LLM_MODEL."
            )

    def _get_json(self, path: str) -> Dict[str, Any]:
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        return self._open_json(request)

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._open_json(request)

    def _open_json(self, request: urllib.request.Request) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - local/user-configured benchmark URL
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"could not reach Ollama at {self.base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {exc}") from exc
