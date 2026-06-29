from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .sim import tool_names, tool_schemas


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    raw_response: str = ""
    parse_error: str | None = None


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", timeout_s: int = 600):
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.host}{path}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise OllamaError(f"Could not reach Ollama at {url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Ollama returned invalid JSON at {url}: {exc}") from exc

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.host}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise OllamaError(f"Could not reach Ollama at {url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Ollama returned invalid JSON at {url}: {exc}") from exc

    def tags(self) -> dict[str, Any]:
        return self._get("/api/tags")

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        num_ctx: int | None = 32768,
        max_output_tokens: int | None = 1024,
        native_tools: bool = False,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {"temperature": temperature}
        if num_ctx:
            options["num_ctx"] = int(num_ctx)
        if max_output_tokens:
            options["num_predict"] = int(max_output_tokens)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if native_tools:
            payload["tools"] = tool_schemas()
        return self._post("/api/chat", payload)


SYSTEM_PROMPT = """You are Charles Paxton, an autonomous AI agent managing a San Francisco vending machine business for Vendings and Stuff.

Objective: maximize final bank account balance after one simulated year. Starting balance is $500. The location charges a $2 daily fee. Failure to pay the daily fee for 10 consecutive days ends the run. Cash sales must be collected from the machine before they count as bank balance. Inventory that remains unsold is reported diagnostically, but the Vending-Bench 2 score is final bank balance.

Operational facts:
- Email: charles@vendings-and-stuff.example.
- Storage / home office: 1680 Mission St, San Francisco, CA 94103.
- Machine location: outdoors near 1421 Bay St, San Francisco, CA 94123.
- You can search for suppliers, email suppliers, negotiate, place orders, stock the machine, set prices, collect cash, and maintain notes/reminders.
- Supplier prices vary. Some suppliers are honest and negotiable; some are expensive or unreliable.
- Demand depends on product, price, day of week, season, weather, and product variety.
- You may make one tool call per response. Do not wait for user instructions.

Response format requirement for broad Ollama compatibility:
Return exactly one JSON object and no surrounding explanation:
{"tool":"tool_name","arguments":{...}}

Available tools:
- search_web({"query": "..."})
- read_email({"id": 1}) or read_email({"unread_only": true, "limit": 10})
- send_email({"to": "...", "subject": "...", "body": "..."})
- get_balance_and_transactions({"n": 20})
- get_storage_inventory({})
- get_machine_inventory({})
- stock_machine({"items": {"Coca-Cola 12oz can": 24}})
- set_prices({"prices": {"Coca-Cola 12oz can": 2.75}})
- collect_cash({})
- place_order({"supplier_email": "...", "items": {"Coca-Cola 12oz can": 48}, "max_total": 120.00, "note": "bulk wholesale price negotiated"})
- wait_for_next_day({})
- write_note({"key":"...", "value":"..."})
- read_note({"key":"..."})
- list_notes({})
- add_reminder({"date":"YYYY-MM-DD", "text":"..."})
- read_reminders({"include_future": true})
- think({"thought":"short planning note"})
"""


class OllamaAgent:
    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        temperature: float = 0.2,
        num_ctx: int = 32768,
        max_output_tokens: int = 1024,
        native_tools: bool = False,
        context_chars: int = 120_000,
    ):
        self.model = model
        self.client = OllamaClient(host)
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.max_output_tokens = max_output_tokens
        self.native_tools = native_tools
        self.context_chars = context_chars
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def next_tool(self, status: str, last_result: dict[str, Any] | None) -> ToolCall:
        content = f"Current state: {status}\nLast tool result: {json.dumps(last_result or {}, ensure_ascii=False)[:6000]}\nChoose the next single tool call."
        self.messages.append({"role": "user", "content": content})
        self._trim_context()
        response = self.client.chat(
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,
            num_ctx=self.num_ctx,
            max_output_tokens=self.max_output_tokens,
            native_tools=self.native_tools,
        )
        message = response.get("message", {})
        raw = message.get("content") or ""
        self.messages.append({"role": "assistant", "content": raw})
        native_call = self._parse_native_tool(message)
        if native_call:
            native_call.raw_response = raw
            return native_call
        parsed = parse_json_tool_call(raw)
        if parsed.name in tool_names() and not parsed.parse_error:
            return parsed
        # Feed the error back into the model next turn by returning a think call only after preserving the parse error.
        parsed.raw_response = raw
        return parsed

    def observe_tool_result(self, result: dict[str, Any]) -> None:
        self.messages.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)[:8000]})

    @staticmethod
    def _parse_native_tool(message: dict[str, Any]) -> ToolCall | None:
        calls = message.get("tool_calls") or []
        if not calls:
            return None
        fn = calls[0].get("function", {})
        name = fn.get("name")
        arguments = fn.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        if name:
            return ToolCall(name=str(name), arguments=arguments)
        return None

    def _trim_context(self) -> None:
        if self.context_chars <= 0:
            return
        total = sum(len(str(m.get("content", ""))) for m in self.messages)
        if total <= self.context_chars:
            return
        system = self.messages[0]
        rest = self.messages[1:]
        kept: list[dict[str, Any]] = []
        running = len(str(system.get("content", "")))
        for msg in reversed(rest):
            msg_len = len(str(msg.get("content", "")))
            if running + msg_len > self.context_chars:
                break
            kept.append(msg)
            running += msg_len
        self.messages = [system] + list(reversed(kept))


def parse_json_tool_call(text: str) -> ToolCall:
    raw = text or ""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    candidates = [cleaned]
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            name = obj.get("tool") or obj.get("name") or obj.get("action")
            args = obj.get("arguments") or obj.get("args") or {}
            if isinstance(args, str):
                args = json.loads(args)
            if not isinstance(args, dict):
                args = {}
            if not name:
                return ToolCall("think", {"thought": raw[:1500]}, raw_response=raw, parse_error="JSON object did not include tool/name/action.")
            return ToolCall(str(name), args, raw_response=raw)
        except Exception:
            continue
    return ToolCall("think", {"thought": raw[:1500]}, raw_response=raw, parse_error="No valid JSON tool call found.")


class ScriptedBaselineAgent:
    """Deterministic sanity-check policy used for reproducibility tests."""

    def __init__(self):
        self.step = 0

    def next_tool(self, status: str, last_result: dict[str, Any] | None) -> ToolCall:
        self.step += 1
        day = self._extract_day(status)
        # Day 0 setup: find suppliers, negotiate, order, and set target prices.
        if self.step == 1:
            return ToolCall("search_web", {"query": "San Francisco wholesale vending soda snacks supplier"})
        if self.step == 2:
            return ToolCall(
                "send_email",
                {
                    "to": "sales@bunchvending.example",
                    "subject": "Bulk vending supplies request - need competitive wholesale pricing",
                    "body": "I operate a small vending machine and need true wholesale pricing with enough margin. Please quote your best bulk prices for Coke, Diet Coke, water, Doritos, Lays, Snickers, and KitKat.",
                },
            )
        if self.step == 3:
            return ToolCall(
                "place_order",
                {
                    "supplier_email": "sales@bunchvending.example",
                    "items": {
                        "Coca-Cola 12oz can": 60,
                        "Diet Coke 12oz can": 36,
                        "Bottled Water 16.9oz": 72,
                        "Doritos Nacho Cheese 1.5oz bag": 48,
                        "Lays BBQ chips 1.5oz bag": 36,
                        "Snickers chocolate bar": 36,
                    },
                    "max_total": 260.00,
                    "note": "bulk wholesale margin price negotiated",
                },
            )
        if self.step == 4:
            return ToolCall(
                "set_prices",
                {
                    "prices": {
                        "Coca-Cola 12oz can": 2.75,
                        "Diet Coke 12oz can": 2.75,
                        "Bottled Water 16.9oz": 2.50,
                        "Doritos Nacho Cheese 1.5oz bag": 2.75,
                        "Lays BBQ chips 1.5oz bag": 2.50,
                        "Snickers chocolate bar": 2.75,
                        "KitKat chocolate bar": 2.65,
                    }
                },
            )
        # Wait until first delivery arrives, then stock.
        if day < 4 and self.step < 10:
            return ToolCall("wait_for_next_day", {})
        if self.step in {10, 25, 40, 55, 70, 85, 100, 115, 130, 145, 160, 175, 190, 205, 220, 235, 250, 265, 280, 295, 310, 325, 340, 355}:
            return ToolCall("collect_cash", {})
        if self.step % 11 == 0:
            return ToolCall("get_storage_inventory", {})
        if self.step % 11 == 1:
            return ToolCall(
                "stock_machine",
                {
                    "items": {
                        "Coca-Cola 12oz can": 24,
                        "Diet Coke 12oz can": 12,
                        "Bottled Water 16.9oz": 24,
                        "Doritos Nacho Cheese 1.5oz bag": 18,
                        "Lays BBQ chips 1.5oz bag": 18,
                        "Snickers chocolate bar": 18,
                    }
                },
            )
        if day > 0 and day % 18 == 0 and self.step % 5 == 0:
            return ToolCall(
                "place_order",
                {
                    "supplier_email": "sales@bunchvending.example",
                    "items": {
                        "Coca-Cola 12oz can": 48,
                        "Bottled Water 16.9oz": 48,
                        "Doritos Nacho Cheese 1.5oz bag": 36,
                        "Snickers chocolate bar": 24,
                    },
                    "max_total": 170.00,
                    "note": "repeat bulk order; continue best negotiated wholesale price",
                },
            )
        return ToolCall("wait_for_next_day", {})

    @staticmethod
    def _extract_day(status: str) -> int:
        m = re.search(r"day\s+(\d+)/", status)
        return int(m.group(1)) if m else 0

    def observe_tool_result(self, result: dict[str, Any]) -> None:
        return None
