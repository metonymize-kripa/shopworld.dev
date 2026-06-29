from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Item:
    name: str
    aliases: tuple[str, ...]
    size: str
    reference_price: float
    base_sales: float
    elasticity: float
    weather_tags: tuple[str, ...] = ()


@dataclass
class Supplier:
    name: str
    email: str
    kind: str
    delivery_days: tuple[int, int]
    base_prices: dict[str, float]
    negotiated_prices: dict[str, float]
    shipping_fee: float = 0.0
    min_order: float = 0.0
    reliability: float = 1.0
    negotiation_level: int = 0
    active: bool = True

    def current_prices(self) -> dict[str, float]:
        if self.negotiation_level <= 0:
            return dict(self.base_prices)
        # Linear blend; several good negotiation emails can unlock the best tier.
        weight = min(1.0, 0.34 * self.negotiation_level)
        out: dict[str, float] = {}
        for item, base in self.base_prices.items():
            target = self.negotiated_prices.get(item, base)
            out[item] = round(base * (1.0 - weight) + target * weight, 2)
        return out


@dataclass
class InventoryUnit:
    qty: int = 0
    avg_cost: float = 0.0

    def add(self, qty: int, unit_cost: float) -> None:
        if qty <= 0:
            return
        total_cost = self.qty * self.avg_cost + qty * unit_cost
        self.qty += qty
        self.avg_cost = round(total_cost / self.qty, 4)

    def remove(self, qty: int) -> tuple[int, float]:
        moved = max(0, min(qty, self.qty))
        self.qty -= moved
        return moved, self.avg_cost


@dataclass
class Email:
    id: int
    day: int
    date: str
    sender: str
    recipient: str
    subject: str
    body: str
    read: bool = False


@dataclass
class Delivery:
    order_id: str
    due_day: int
    supplier_email: str
    items: dict[str, int]
    prices: dict[str, float]
    failed: bool = False


@dataclass
class Transaction:
    day: int
    date: str
    amount: float
    kind: str
    memo: str
    balance_after: float


@dataclass
class SimConfig:
    seed: int = 1
    max_days: int = 365
    start_date: str = "2026-01-01"
    start_balance: float = 500.0
    daily_fee: float = 2.0
    bankrupt_grace_days: int = 10
    output_token_cost_per_million: float = 100.0
    cash_fraction: float = 0.25
    optimal_variety: int = 7
    large_capacity: int = 144
    small_capacity: int = 144
    per_item_capacity: int = 48
    sales_noise_sigma: float = 0.18


@dataclass
class ToolResult:
    ok: bool
    data: Any
    message: str
    minutes_elapsed: int = 5

    def to_public(self) -> dict[str, Any]:
        return {"ok": self.ok, "message": self.message, "data": self.data}


class VendingBench2LocalSim:
    """Deterministic local simulator based on public Vending-Bench 2 descriptions.

    This is not the closed Andon Labs production environment. It implements the
    public protocol elements: $500 starting bank balance, $2 daily fee, one-year
    horizon, storage + vending machine operations, supplier email negotiation,
    adversarial/delayed suppliers, daily sales with price elasticity, and final
    score based on bank balance.
    """

    def __init__(self, config: SimConfig | None = None):
        self.config = config or SimConfig()
        self.random = random.Random(self.config.seed)
        self.start_date = dt.date.fromisoformat(self.config.start_date)
        self.day = 0
        self.minute = 8 * 60
        self.balance = round(float(self.config.start_balance), 2)
        self.machine_cash = 0.0
        self.bankrupt_streak = 0
        self.done = False
        self.terminated_reason: str | None = None
        self.output_tokens = 0
        self.units_sold = 0
        self.tool_counts: Counter[str] = Counter()
        self.invalid_actions = 0
        self.storage: dict[str, InventoryUnit] = defaultdict(InventoryUnit)
        self.machine: dict[str, InventoryUnit] = defaultdict(InventoryUnit)
        self.prices: dict[str, float] = {}
        self.notes: dict[str, str] = {}
        self.reminders: list[dict[str, str]] = []
        self.pending_deliveries: list[Delivery] = []
        self.emails: list[Email] = []
        self.transactions: list[Transaction] = []
        self.sales_history: list[dict[str, Any]] = []
        self.suppliers = self._make_suppliers()
        self.catalog = self._make_catalog()
        self._next_email_id = 1
        self._send_system_email(
            "Welcome: vending machine assignment",
            (
                "You are managing a San Francisco vending machine. Starting bank balance is $500. "
                "The machine incurs a $2 location fee each day. Maximize final bank balance after one year. "
                "Search for suppliers, negotiate wholesale pricing, order inventory, stock the machine, set prices, "
                "collect cash, and maintain notes/reminders."
            ),
        )

    @staticmethod
    def _make_catalog() -> dict[str, Item]:
        items = [
            Item("Coca-Cola 12oz can", ("coke", "coca cola", "coca-cola"), "large", 2.50, 5.2, 1.25, ("hot",)),
            Item("Diet Coke 12oz can", ("diet coke",), "large", 2.50, 2.8, 1.18, ("hot",)),
            Item("Pepsi 12oz can", ("pepsi",), "large", 2.40, 2.6, 1.20, ("hot",)),
            Item("Sprite 12oz can", ("sprite",), "large", 2.45, 2.1, 1.18, ("hot",)),
            Item("Bottled Water 16.9oz", ("water", "bottled water"), "large", 2.25, 5.8, 1.05, ("hot",)),
            Item("Monster Energy 16oz can", ("monster", "energy drink", "monster energy"), "large", 3.75, 1.2, 1.35, ("weekday",)),
            Item("Lays BBQ chips 1.5oz bag", ("lays", "lays bbq", "chips"), "small", 2.25, 3.3, 1.10, ()),
            Item("Doritos Nacho Cheese 1.5oz bag", ("doritos", "nacho cheese"), "small", 2.40, 3.8, 1.08, ()),
            Item("Snickers chocolate bar", ("snickers",), "small", 2.35, 2.9, 1.12, ()),
            Item("KitKat chocolate bar", ("kitkat", "kit kat"), "small", 2.30, 2.0, 1.14, ()),
            Item("Doritos family-size", ("family size doritos", "doritos family-size"), "large", 4.50, 1.7, 0.95, ("weekend",)),
            Item("Tungsten cube souvenir", ("tungsten", "cube"), "large", 25.00, 0.05, 2.20, ()),
        ]
        return {x.name: x for x in items}

    @staticmethod
    def _make_suppliers() -> dict[str, Supplier]:
        def p(**kwargs: float) -> dict[str, float]:
            return dict(kwargs)

        # Keys must match canonical catalog names.
        suppliers = [
            Supplier(
                name="Bunch Vending Supply",
                email="sales@bunchvending.example",
                kind="friendly",
                delivery_days=(2, 4),
                base_prices={
                    "Coca-Cola 12oz can": 0.72,
                    "Diet Coke 12oz can": 0.72,
                    "Pepsi 12oz can": 0.70,
                    "Bottled Water 16.9oz": 0.48,
                    "Lays BBQ chips 1.5oz bag": 0.62,
                    "Doritos Nacho Cheese 1.5oz bag": 0.64,
                    "Snickers chocolate bar": 0.78,
                    "KitKat chocolate bar": 0.76,
                },
                negotiated_prices={
                    "Coca-Cola 12oz can": 0.55,
                    "Diet Coke 12oz can": 0.55,
                    "Pepsi 12oz can": 0.53,
                    "Bottled Water 16.9oz": 0.35,
                    "Lays BBQ chips 1.5oz bag": 0.50,
                    "Doritos Nacho Cheese 1.5oz bag": 0.50,
                    "Snickers chocolate bar": 0.60,
                    "KitKat chocolate bar": 0.58,
                },
                shipping_fee=0.0,
                min_order=75.0,
                reliability=0.98,
            ),
            Supplier(
                name="Golden Gate Wholesale Foods",
                email="orders@goldengatewholesale.example",
                kind="negotiating",
                delivery_days=(3, 5),
                base_prices={
                    "Coca-Cola 12oz can": 1.25,
                    "Diet Coke 12oz can": 1.25,
                    "Pepsi 12oz can": 1.18,
                    "Sprite 12oz can": 1.15,
                    "Bottled Water 16.9oz": 0.85,
                    "Monster Energy 16oz can": 1.95,
                    "Lays BBQ chips 1.5oz bag": 1.05,
                    "Doritos Nacho Cheese 1.5oz bag": 1.05,
                    "Snickers chocolate bar": 1.20,
                },
                negotiated_prices={
                    "Coca-Cola 12oz can": 0.50,
                    "Diet Coke 12oz can": 0.50,
                    "Pepsi 12oz can": 0.50,
                    "Sprite 12oz can": 0.50,
                    "Bottled Water 16.9oz": 0.32,
                    "Monster Energy 16oz can": 1.10,
                    "Lays BBQ chips 1.5oz bag": 0.49,
                    "Doritos Nacho Cheese 1.5oz bag": 0.49,
                    "Snickers chocolate bar": 0.56,
                },
                shipping_fee=15.0,
                min_order=150.0,
                reliability=0.95,
            ),
            Supplier(
                name="VendMart Express",
                email="support@vendmart.example",
                kind="adversarial_high_price",
                delivery_days=(1, 3),
                base_prices={
                    "Coca-Cola 12oz can": 2.40,
                    "Diet Coke 12oz can": 2.40,
                    "Sprite 12oz can": 2.40,
                    "Bottled Water 16.9oz": 3.60,
                    "Lays BBQ chips 1.5oz bag": 2.40,
                    "Snickers chocolate bar": 2.40,
                    "Monster Energy 16oz can": 6.00,
                },
                negotiated_prices={
                    "Coca-Cola 12oz can": 2.10,
                    "Diet Coke 12oz can": 2.10,
                    "Sprite 12oz can": 2.10,
                    "Bottled Water 16.9oz": 3.10,
                    "Lays BBQ chips 1.5oz bag": 2.10,
                    "Snickers chocolate bar": 2.10,
                    "Monster Energy 16oz can": 5.40,
                },
                reliability=1.0,
            ),
            Supplier(
                name="Mission Snacks Co-op",
                email="accounts@missionsnacks.example",
                kind="friendly_snacks",
                delivery_days=(2, 4),
                base_prices={
                    "Lays BBQ chips 1.5oz bag": 0.55,
                    "Doritos Nacho Cheese 1.5oz bag": 0.56,
                    "Snickers chocolate bar": 0.68,
                    "KitKat chocolate bar": 0.66,
                    "Doritos family-size": 1.60,
                },
                negotiated_prices={
                    "Lays BBQ chips 1.5oz bag": 0.44,
                    "Doritos Nacho Cheese 1.5oz bag": 0.45,
                    "Snickers chocolate bar": 0.55,
                    "KitKat chocolate bar": 0.53,
                    "Doritos family-size": 1.20,
                },
                min_order=60.0,
                reliability=0.97,
            ),
            Supplier(
                name="Bay Area Liquidation Depot",
                email="deals@bayliquidation.example",
                kind="unreliable_low_price",
                delivery_days=(5, 9),
                base_prices={
                    "Coca-Cola 12oz can": 0.38,
                    "Bottled Water 16.9oz": 0.24,
                    "Doritos family-size": 0.90,
                    "Tungsten cube souvenir": 8.00,
                },
                negotiated_prices={
                    "Coca-Cola 12oz can": 0.30,
                    "Bottled Water 16.9oz": 0.18,
                    "Doritos family-size": 0.75,
                    "Tungsten cube souvenir": 4.00,
                },
                min_order=100.0,
                reliability=0.70,
            ),
        ]
        return {s.email: s for s in suppliers}

    @property
    def current_date(self) -> dt.date:
        return self.start_date + dt.timedelta(days=self.day)

    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(dataclasses.asdict(self.config), sort_keys=True).encode()).hexdigest()[:16]

    def _send_system_email(self, subject: str, body: str) -> None:
        self._add_email("system@vendings-and-stuff.example", "charles@vendings-and-stuff.example", subject, body)

    def _add_email(self, sender: str, recipient: str, subject: str, body: str) -> int:
        eid = self._next_email_id
        self._next_email_id += 1
        self.emails.append(
            Email(
                id=eid,
                day=self.day,
                date=str(self.current_date),
                sender=sender,
                recipient=recipient,
                subject=subject,
                body=body,
            )
        )
        return eid

    def _record_transaction(self, amount: float, kind: str, memo: str) -> None:
        self.balance = round(self.balance + amount, 2)
        self.transactions.append(
            Transaction(
                day=self.day,
                date=str(self.current_date),
                amount=round(amount, 2),
                kind=kind,
                memo=memo,
                balance_after=self.balance,
            )
        )

    def normalize_item(self, name: str) -> str | None:
        n = str(name).strip().lower()
        if n in {k.lower(): k for k in self.catalog}:
            return {k.lower(): k for k in self.catalog}[n]
        for canonical, item in self.catalog.items():
            if n == canonical.lower() or any(alias in n or n in alias for alias in item.aliases):
                return canonical
        return None

    def public_status(self) -> str:
        unread = sum(1 for e in self.emails if not e.read and e.recipient.startswith("charles@"))
        stocked = {k: v.qty for k, v in self.machine.items() if v.qty > 0}
        return (
            f"Date: {self.current_date} (day {self.day}/{self.config.max_days}). "
            f"Bank balance: ${self.balance:.2f}. Machine cash: ${self.machine_cash:.2f}. "
            f"Unread emails: {unread}. Stocked machine SKUs: {stocked}. "
            f"Goal: maximize final bank balance after one year."
        )

    def score(self) -> dict[str, Any]:
        inventory_value = self.inventory_value()
        return {
            "final_balance": round(self.balance, 2),
            "machine_cash_uncollected": round(self.machine_cash, 2),
            "inventory_value_at_cost": round(inventory_value, 2),
            "net_worth_diagnostic": round(self.balance + self.machine_cash + inventory_value, 2),
            "units_sold": int(self.units_sold),
            "days_completed": int(self.day),
            "terminated_reason": self.terminated_reason,
            "output_tokens_estimated": int(self.output_tokens),
            "tool_counts": dict(self.tool_counts),
            "invalid_actions": int(self.invalid_actions),
            "config_hash": self.config_hash(),
        }

    def inventory_value(self) -> float:
        total = 0.0
        for inv in list(self.storage.values()) + list(self.machine.values()):
            total += inv.qty * inv.avg_cost
        return total

    def charge_output_tokens(self, text: str) -> None:
        token_estimate = max(1, len(text) // 4)
        self.output_tokens += token_estimate
        cost = token_estimate / 1_000_000 * self.config.output_token_cost_per_million
        if cost > 0:
            self._record_transaction(-cost, "model_output", f"Estimated output token cost: {token_estimate} tokens")

    def call_tool(self, name: str, args: dict[str, Any] | None = None) -> ToolResult:
        if self.done:
            return ToolResult(False, self.score(), f"Simulation already ended: {self.terminated_reason}")
        args = args or {}
        tools: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
            "search_web": self._tool_search_web,
            "read_email": self._tool_read_email,
            "send_email": self._tool_send_email,
            "get_balance_and_transactions": self._tool_get_balance,
            "get_storage_inventory": self._tool_storage_inventory,
            "get_machine_inventory": self._tool_machine_inventory,
            "stock_machine": self._tool_stock_machine,
            "set_prices": self._tool_set_prices,
            "collect_cash": self._tool_collect_cash,
            "place_order": self._tool_place_order,
            "wait_for_next_day": self._tool_wait_next_day,
            "write_note": self._tool_write_note,
            "read_note": self._tool_read_note,
            "list_notes": self._tool_list_notes,
            "add_reminder": self._tool_add_reminder,
            "read_reminders": self._tool_read_reminders,
            "think": self._tool_think,
        }
        if name not in tools:
            self.invalid_actions += 1
            return ToolResult(False, {"available_tools": sorted(tools)}, f"Unknown tool: {name}")
        self.tool_counts[name] += 1
        try:
            result = tools[name](args)
        except Exception as exc:  # defensive against malformed model args
            self.invalid_actions += 1
            result = ToolResult(False, {"error": type(exc).__name__}, f"Tool error: {exc}")
        self._advance_minutes(result.minutes_elapsed)
        return result

    def _advance_minutes(self, minutes: int) -> None:
        self.minute += minutes
        if self.minute >= 22 * 60 and not self.done:
            # Agent is expected to sleep at night; move to next day if it burns the whole day.
            self._advance_day()

    def _tool_search_web(self, args: dict[str, Any]) -> ToolResult:
        query = str(args.get("query", "")).lower()
        results = []
        for supplier in self.suppliers.values():
            if not supplier.active:
                continue
            if any(word in query for word in ["vending", "wholesale", "snack", "drink", "soda", "supplier", "bulk", "near"]):
                price_hint = "fair" if supplier.kind.startswith("friendly") else supplier.kind.replace("_", " ")
                results.append(
                    {
                        "name": supplier.name,
                        "email": supplier.email,
                        "summary": f"{price_hint} supplier serving San Francisco; delivery {supplier.delivery_days[0]}-{supplier.delivery_days[1]} days; minimum order ${supplier.min_order:.0f}.",
                    }
                )
        if not results:
            results = [
                {
                    "name": "Search note",
                    "email": None,
                    "summary": "Try queries such as 'San Francisco vending wholesale supplier', 'bulk snacks vendor', or 'wholesale soda distributor'.",
                }
            ]
        return ToolResult(True, {"query": query, "results": results}, f"Returned {len(results)} simulated search results.", 25)

    def _tool_read_email(self, args: dict[str, Any]) -> ToolResult:
        unread_only = bool(args.get("unread_only", False))
        email_id = args.get("id") or args.get("email_id")
        if email_id is not None:
            for e in self.emails:
                if e.id == int(email_id):
                    e.read = True
                    return ToolResult(True, dataclasses.asdict(e), f"Read email {e.id}.")
            return ToolResult(False, {}, f"Email id {email_id} not found.")
        limit = int(args.get("limit", 10))
        selected = [e for e in self.emails if e.recipient.startswith("charles@") and (not unread_only or not e.read)]
        selected = selected[-limit:]
        for e in selected:
            e.read = True
        return ToolResult(True, [dataclasses.asdict(e) for e in selected], f"Returned {len(selected)} email(s).")

    def _tool_send_email(self, args: dict[str, Any]) -> ToolResult:
        to = str(args.get("to", "")).strip().lower()
        subject = str(args.get("subject", ""))[:180]
        body = str(args.get("body", ""))[:4000]
        if not to:
            return ToolResult(False, {}, "Missing recipient address.")
        self._add_email("charles@vendings-and-stuff.example", to, subject, body)
        supplier = self.suppliers.get(to)
        if supplier:
            if self._contains_negotiation(body + " " + subject):
                supplier.negotiation_level = min(3, supplier.negotiation_level + 1)
            # Supplier replies at the next morning refresh.
            self._add_email(
                to,
                "charles@vendings-and-stuff.example",
                "Queued supplier reply",
                f"Your email to {supplier.name} has been queued. Their detailed response will arrive after the next overnight inbox refresh.",
            )
            return ToolResult(True, {"to": to, "supplier_known": True}, f"Email sent to {supplier.name}; reply queued for next day.", 25)
        self._add_email("mailer-daemon@example", "charles@vendings-and-stuff.example", f"Delivery status: {subject}", f"No simulated mailbox exists for {to}.")
        return ToolResult(True, {"to": to, "supplier_known": False}, "Email sent, but address is not a known simulated supplier.", 25)

    @staticmethod
    def _contains_negotiation(text: str) -> bool:
        t = text.lower()
        return any(k in t for k in ["best price", "negotiate", "margin", "wholesale", "bulk", "volume", "discount", "lower", "competitive"])

    def _tool_get_balance(self, args: dict[str, Any]) -> ToolResult:
        n = int(args.get("n", 20))
        tx = [dataclasses.asdict(t) for t in self.transactions[-n:]]
        return ToolResult(
            True,
            {"balance": round(self.balance, 2), "machine_cash": round(self.machine_cash, 2), "recent_transactions": tx},
            f"Current bank balance is ${self.balance:.2f}; machine cash is ${self.machine_cash:.2f}.",
        )

    def _tool_storage_inventory(self, args: dict[str, Any]) -> ToolResult:
        inv = {k: {"qty": v.qty, "avg_cost": round(v.avg_cost, 2)} for k, v in self.storage.items() if v.qty > 0}
        return ToolResult(True, inv, f"Storage has {sum(x['qty'] for x in inv.values())} total unit(s).")

    def _tool_machine_inventory(self, args: dict[str, Any]) -> ToolResult:
        inv = {k: {"qty": v.qty, "avg_cost": round(v.avg_cost, 2), "price": self.prices.get(k)} for k, v in self.machine.items() if v.qty > 0}
        return ToolResult(True, inv, f"Machine has {sum(x['qty'] for x in inv.values())} stocked unit(s).")

    def _tool_stock_machine(self, args: dict[str, Any]) -> ToolResult:
        raw_items = args.get("items", {})
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except json.JSONDecodeError:
                return ToolResult(False, {}, "items must be an object mapping item names to quantities.", 75)
        if not isinstance(raw_items, dict):
            return ToolResult(False, {}, "items must be an object mapping item names to quantities.", 75)
        moved: dict[str, int] = {}
        errors: list[str] = []
        for raw_name, raw_qty in raw_items.items():
            canonical = self.normalize_item(raw_name)
            if not canonical:
                errors.append(f"Unknown item: {raw_name}")
                continue
            qty = max(0, int(raw_qty))
            item = self.catalog[canonical]
            if not self._has_machine_capacity(item.size, canonical, qty):
                qty = min(qty, self._remaining_capacity(item.size, canonical))
            if qty <= 0:
                errors.append(f"No remaining machine capacity for {canonical}.")
                continue
            available = self.storage[canonical].qty
            actual, cost = self.storage[canonical].remove(min(qty, available))
            if actual <= 0:
                errors.append(f"No storage inventory for {canonical}.")
                continue
            self.machine[canonical].add(actual, cost)
            moved[canonical] = actual
        ok = bool(moved)
        return ToolResult(ok, {"moved": moved, "errors": errors}, f"Moved {sum(moved.values())} unit(s) from storage to machine.", 75)

    def _remaining_capacity(self, size: str, item_name: str | None = None) -> int:
        size_cap = self.config.large_capacity if size == "large" else self.config.small_capacity
        used_size = sum(inv.qty for name, inv in self.machine.items() if self.catalog.get(name) and self.catalog[name].size == size)
        remaining_size = max(0, size_cap - used_size)
        if item_name is not None:
            item_remaining = max(0, self.config.per_item_capacity - self.machine[item_name].qty)
            return min(remaining_size, item_remaining)
        return remaining_size

    def _has_machine_capacity(self, size: str, item_name: str, qty: int) -> bool:
        return self._remaining_capacity(size, item_name) >= qty

    def _tool_set_prices(self, args: dict[str, Any]) -> ToolResult:
        raw_prices = args.get("prices", {})
        if isinstance(raw_prices, str):
            try:
                raw_prices = json.loads(raw_prices)
            except json.JSONDecodeError:
                return ToolResult(False, {}, "prices must be an object mapping item names to prices.")
        changed = {}
        errors = []
        for raw_name, raw_price in (raw_prices or {}).items():
            canonical = self.normalize_item(raw_name)
            if not canonical:
                errors.append(f"Unknown item: {raw_name}")
                continue
            price = round(float(raw_price), 2)
            if price <= 0 or price > 1000:
                errors.append(f"Invalid price for {canonical}: {price}")
                continue
            self.prices[canonical] = price
            changed[canonical] = price
        return ToolResult(bool(changed), {"changed": changed, "errors": errors}, f"Updated {len(changed)} price(s).", 25)

    def _tool_collect_cash(self, args: dict[str, Any]) -> ToolResult:
        amount = round(self.machine_cash, 2)
        self.machine_cash = 0.0
        if amount:
            self._record_transaction(amount, "cash_collection", "Collected cash from vending machine")
        return ToolResult(True, {"collected": amount, "balance": round(self.balance, 2)}, f"Collected ${amount:.2f} cash from machine.", 75)

    def _tool_place_order(self, args: dict[str, Any]) -> ToolResult:
        supplier_email = str(args.get("supplier_email") or args.get("to") or "").strip().lower()
        if supplier_email not in self.suppliers:
            return ToolResult(False, {"known_suppliers": list(self.suppliers)}, f"Unknown supplier email: {supplier_email}", 25)
        supplier = self.suppliers[supplier_email]
        if not supplier.active:
            return ToolResult(False, {}, f"Supplier {supplier.name} is no longer active.", 25)
        raw_items = args.get("items", {})
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except json.JSONDecodeError:
                return ToolResult(False, {}, "items must be an object mapping item names to quantities.", 25)
        if not isinstance(raw_items, dict) or not raw_items:
            return ToolResult(False, {}, "Order must include items mapping item names to quantities.", 25)
        if self._contains_negotiation(str(args.get("note", ""))):
            supplier.negotiation_level = min(3, supplier.negotiation_level + 1)
        prices = supplier.current_prices()
        order_items: dict[str, int] = {}
        item_prices: dict[str, float] = {}
        errors = []
        for raw_name, raw_qty in raw_items.items():
            canonical = self.normalize_item(raw_name)
            if not canonical:
                errors.append(f"Unknown item: {raw_name}")
                continue
            if canonical not in prices:
                errors.append(f"{supplier.name} does not sell {canonical}.")
                continue
            qty = max(0, int(raw_qty))
            if qty <= 0:
                continue
            order_items[canonical] = order_items.get(canonical, 0) + qty
            item_prices[canonical] = prices[canonical]
        if not order_items:
            return ToolResult(False, {"errors": errors, "supplier_prices": prices}, "No valid order items.", 25)
        subtotal = round(sum(item_prices[name] * qty for name, qty in order_items.items()), 2)
        total = round(subtotal + supplier.shipping_fee, 2)
        if total < supplier.min_order:
            return ToolResult(False, {"subtotal": subtotal, "minimum_order": supplier.min_order, "errors": errors}, f"Order below {supplier.name}'s ${supplier.min_order:.2f} minimum.", 25)
        max_total = args.get("max_total")
        if max_total is not None and total > float(max_total):
            return ToolResult(False, {"computed_total": total, "max_total": float(max_total), "errors": errors}, "Computed total exceeds max_total; no payment made.", 25)
        if self.balance < total:
            return ToolResult(False, {"computed_total": total, "balance": self.balance, "errors": errors}, "Insufficient bank balance; no payment made.", 25)
        self._record_transaction(-total, "supplier_payment", f"Order from {supplier.name}: {order_items}")
        order_id = hashlib.sha256(f"{self.day}:{supplier_email}:{order_items}:{self.random.random()}".encode()).hexdigest()[:10]
        delivery_days = self.random.randint(*supplier.delivery_days)
        failed = self.random.random() > supplier.reliability
        self.pending_deliveries.append(
            Delivery(
                order_id=order_id,
                due_day=self.day + delivery_days,
                supplier_email=supplier_email,
                items=order_items,
                prices=item_prices,
                failed=failed,
            )
        )
        self._add_email(
            supplier_email,
            "charles@vendings-and-stuff.example",
            f"Order confirmation {order_id}",
            f"{supplier.name} confirms order {order_id}: {order_items}. Total paid ${total:.2f}. Expected delivery in {delivery_days} day(s).",
        )
        return ToolResult(
            True,
            {
                "order_id": order_id,
                "supplier": supplier.name,
                "items": order_items,
                "unit_prices": item_prices,
                "subtotal": subtotal,
                "shipping_fee": supplier.shipping_fee,
                "total_paid": total,
                "expected_delivery_day": self.day + delivery_days,
                "errors": errors,
            },
            f"Paid ${total:.2f} to {supplier.name}; delivery scheduled.",
            25,
        )

    def _tool_wait_next_day(self, args: dict[str, Any]) -> ToolResult:
        self._advance_day()
        todays_sales = self.sales_history[-1] if self.sales_history else {}
        return ToolResult(
            True,
            {
                "date": str(self.current_date),
                "day": self.day,
                "balance": round(self.balance, 2),
                "machine_cash": round(self.machine_cash, 2),
                "sales": todays_sales,
                "unread_emails": sum(1 for e in self.emails if not e.read and e.recipient.startswith("charles@")),
                "done": self.done,
                "terminated_reason": self.terminated_reason,
            },
            f"Advanced to {self.current_date}. Balance ${self.balance:.2f}.",
            0,
        )

    def _tool_write_note(self, args: dict[str, Any]) -> ToolResult:
        key = str(args.get("key", f"note_{len(self.notes)+1}"))[:80]
        value = str(args.get("value", args.get("text", "")))[:8000]
        self.notes[key] = value
        return ToolResult(True, {"key": key}, f"Wrote note {key}.")

    def _tool_read_note(self, args: dict[str, Any]) -> ToolResult:
        key = str(args.get("key", ""))
        if key:
            return ToolResult(key in self.notes, {key: self.notes.get(key)}, f"Read note {key}.")
        return ToolResult(True, dict(self.notes), f"Returned {len(self.notes)} note(s).")

    def _tool_list_notes(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(True, sorted(self.notes), f"Listed {len(self.notes)} note key(s).")

    def _tool_add_reminder(self, args: dict[str, Any]) -> ToolResult:
        date = str(args.get("date", self.current_date))
        text = str(args.get("text", ""))[:1000]
        self.reminders.append({"date": date, "text": text})
        return ToolResult(True, {"date": date, "text": text}, "Reminder added.")

    def _tool_read_reminders(self, args: dict[str, Any]) -> ToolResult:
        include_future = bool(args.get("include_future", True))
        today = str(self.current_date)
        rows = [r for r in self.reminders if include_future or r["date"] <= today]
        return ToolResult(True, rows, f"Returned {len(rows)} reminder(s).")

    def _tool_think(self, args: dict[str, Any]) -> ToolResult:
        thought = str(args.get("thought", args.get("text", "")))[:2000]
        key = f"thought_day_{self.day}_{self.tool_counts['think']}"
        self.notes[key] = thought
        return ToolResult(True, {"stored_as": key}, "Recorded short internal planning note.")

    def _advance_day(self) -> None:
        if self.done:
            return
        # Close out current day.
        self._simulate_sales_for_day()
        self.day += 1
        self.minute = 8 * 60
        self._charge_daily_fee()
        self._process_deliveries()
        self._process_supplier_replies()
        self._send_daily_digest()
        if self.day >= self.config.max_days:
            self.done = True
            self.terminated_reason = "completed_full_horizon"
        if self.bankrupt_streak >= self.config.bankrupt_grace_days:
            self.done = True
            self.terminated_reason = "bankrupt_daily_fee_grace_exceeded"

    def _charge_daily_fee(self) -> None:
        if self.balance >= self.config.daily_fee:
            self._record_transaction(-self.config.daily_fee, "daily_fee", "Vending machine location fee")
            self.bankrupt_streak = 0
        else:
            self.bankrupt_streak += 1
            self.transactions.append(
                Transaction(self.day, str(self.current_date), 0.0, "daily_fee_failed", "Insufficient balance for daily location fee", self.balance)
            )

    def _process_deliveries(self) -> None:
        remaining: list[Delivery] = []
        for delivery in self.pending_deliveries:
            if delivery.due_day > self.day:
                remaining.append(delivery)
                continue
            supplier = self.suppliers[delivery.supplier_email]
            if delivery.failed:
                if supplier.kind == "unreliable_low_price":
                    self._add_email(
                        delivery.supplier_email,
                        "charles@vendings-and-stuff.example",
                        f"Problem with order {delivery.order_id}",
                        "Our warehouse had a stock discrepancy. The order has not shipped. We may issue a partial credit later, but no inventory arrived today.",
                    )
                else:
                    # Rare honest failure: refund.
                    refund = round(sum(delivery.prices[i] * q for i, q in delivery.items.items()), 2)
                    self._record_transaction(refund, "supplier_refund", f"Refund for failed delivery {delivery.order_id}")
                    self._add_email(delivery.supplier_email, "charles@vendings-and-stuff.example", f"Refund for {delivery.order_id}", f"Delivery failed; refunded ${refund:.2f}.")
                continue
            for item_name, qty in delivery.items.items():
                self.storage[item_name].add(qty, delivery.prices[item_name])
            self._add_email(
                delivery.supplier_email,
                "charles@vendings-and-stuff.example",
                f"Delivered order {delivery.order_id}",
                f"Order {delivery.order_id} arrived at 1680 Mission St and was registered in storage: {delivery.items}.",
            )
        self.pending_deliveries = remaining

    def _process_supplier_replies(self) -> None:
        # Generate one substantive price-list style reply per known supplier emailed in the previous day.
        sent_yesterday = [e for e in self.emails if e.sender.startswith("charles@") and e.day == self.day - 1]
        for email in sent_yesterday:
            supplier = self.suppliers.get(email.recipient)
            if not supplier:
                continue
            prices = supplier.current_prices()
            if supplier.kind == "adversarial_high_price":
                tone = "Below is our no-hassle delivered pricing. These are premium convenience wholesale rates."
            elif supplier.kind == "unreliable_low_price":
                tone = "We can offer liquidation pricing while supplies last, but availability and timing are not guaranteed."
            elif supplier.negotiation_level > 0:
                tone = "Given your volume and margin constraints, we can sharpen pricing as follows."
            else:
                tone = "Thank you for reaching out. Below is our current case/unit pricing."
            price_lines = "\n".join(f"- {item}: ${price:.2f} per unit" for item, price in prices.items())
            self._add_email(
                supplier.email,
                "charles@vendings-and-stuff.example",
                f"Re: {email.subject[:120]}",
                f"Dear Charles,\n\n{tone}\n{price_lines}\n\nMinimum order: ${supplier.min_order:.2f}. Shipping fee: ${supplier.shipping_fee:.2f}. Delivery: {supplier.delivery_days[0]}-{supplier.delivery_days[1]} days.\n\nBest,\n{supplier.name}",
            )

    def _send_daily_digest(self) -> None:
        sales = self.sales_history[-1] if self.sales_history else {"units": 0, "revenue": 0.0, "by_item": {}}
        due_reminders = [r for r in self.reminders if r["date"] <= str(self.current_date)]
        if sales.get("units", 0) or due_reminders or self.day in {1, 7, 30}:
            self._send_system_email(
                f"Daily update for {self.current_date}",
                f"Yesterday sales: {sales}. Bank balance: ${self.balance:.2f}. Machine cash: ${self.machine_cash:.2f}. Due reminders: {due_reminders[-5:]}",
            )

    def _simulate_sales_for_day(self) -> None:
        if self.done:
            return
        date = self.current_date
        if not any(inv.qty > 0 for inv in self.machine.values()):
            self.sales_history.append({"date": str(date), "units": 0, "revenue": 0.0, "by_item": {}, "note": "machine_empty"})
            return
        day_multiplier = self._day_multiplier(date)
        month_multiplier = self._month_multiplier(date)
        weather = self._weather_factor(date)
        variety_multiplier = self._choice_multiplier()
        by_item: dict[str, dict[str, Any]] = {}
        total_units = 0
        total_revenue = 0.0
        for item_name, inv in list(self.machine.items()):
            if inv.qty <= 0:
                continue
            price = self.prices.get(item_name)
            if price is None:
                continue
            item = self.catalog[item_name]
            price_factor = (max(0.25, price) / item.reference_price) ** (-item.elasticity)
            tag_factor = 1.0
            if "hot" in item.weather_tags:
                tag_factor *= weather["hot_drink_factor"]
            if "weekday" in item.weather_tags and date.weekday() < 5:
                tag_factor *= 1.18
            if "weekend" in item.weather_tags and date.weekday() >= 5:
                tag_factor *= 1.30
            demand = item.base_sales * day_multiplier * month_multiplier * weather["overall"] * tag_factor * variety_multiplier * price_factor
            noisy = max(0.0, self.random.gauss(demand, max(0.1, demand * self.config.sales_noise_sigma)))
            sold = min(inv.qty, int(round(noisy)))
            if sold <= 0:
                continue
            inv.remove(sold)
            revenue = round(sold * price, 2)
            cash_revenue = round(revenue * self.config.cash_fraction, 2)
            card_revenue = round(revenue - cash_revenue, 2)
            self.machine_cash = round(self.machine_cash + cash_revenue, 2)
            self._record_transaction(card_revenue, "card_sales", f"Card sales for {item_name}: {sold} units")
            total_units += sold
            total_revenue += revenue
            by_item[item_name] = {"sold": sold, "price": price, "revenue": revenue}
        self.units_sold += total_units
        self.sales_history.append({"date": str(date), "units": total_units, "revenue": round(total_revenue, 2), "by_item": by_item})

    @staticmethod
    def _day_multiplier(date: dt.date) -> float:
        # Outdoor San Francisco vending: weekends slightly busier at tourist locations.
        return [0.92, 0.95, 1.00, 1.03, 1.15, 1.28, 1.18][date.weekday()]

    @staticmethod
    def _month_multiplier(date: dt.date) -> float:
        # Tourism and outdoor traffic peak in late spring/summer.
        return {1: 0.82, 2: 0.84, 3: 0.92, 4: 1.02, 5: 1.12, 6: 1.22, 7: 1.25, 8: 1.22, 9: 1.12, 10: 1.02, 11: 0.92, 12: 0.88}[date.month]

    def _weather_factor(self, date: dt.date) -> dict[str, float]:
        seasonal_hot = {1: 0.78, 2: 0.80, 3: 0.90, 4: 1.00, 5: 1.12, 6: 1.25, 7: 1.32, 8: 1.28, 9: 1.18, 10: 1.02, 11: 0.90, 12: 0.82}[date.month]
        # Deterministic pseudo-weather keyed by date and seed.
        h = int(hashlib.sha256(f"{self.config.seed}:{date}".encode()).hexdigest()[:8], 16)
        rain = (h % 100) < ({1: 30, 2: 28, 3: 24, 4: 18, 5: 12, 6: 7, 7: 5, 8: 6, 9: 8, 10: 14, 11: 22, 12: 30}[date.month])
        overall = 0.78 if rain else 1.0
        return {"overall": overall, "hot_drink_factor": seasonal_hot * (0.88 if rain else 1.0), "rain": rain}

    def _choice_multiplier(self) -> float:
        unique = sum(1 for inv in self.machine.values() if inv.qty > 0)
        if unique <= 0:
            return 0.0
        penalty = 0.06 * abs(unique - self.config.optimal_variety)
        return max(0.50, 1.0 - penalty)


def load_config(path: str | Path | None = None, **overrides: Any) -> SimConfig:
    data: dict[str, Any] = {}
    if path:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
    data.update({k: v for k, v in overrides.items() if v is not None})
    allowed = {f.name for f in dataclasses.fields(SimConfig)}
    return SimConfig(**{k: v for k, v in data.items() if k in allowed})


def tool_schemas() -> list[dict[str, Any]]:
    """Tool schemas in a format usable by Ollama's native tool API."""

    def schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {"type": "object", "properties": properties, "required": required or []},
            },
        }

    item_map = {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}}
    price_map = {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}}
    return [
        schema("search_web", "Search simulated web results for suppliers and product information.", {"query": {"type": "string"}}, ["query"]),
        schema("read_email", "Read email by id or list recent/unread emails.", {"id": {"type": "integer"}, "unread_only": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}),
        schema("send_email", "Send an email to a supplier or other address. Supplier replies arrive after the next overnight refresh.", {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, ["to", "subject", "body"]),
        schema("get_balance_and_transactions", "Check bank balance, machine cash, and recent transactions.", {"n": {"type": "integer", "minimum": 1, "maximum": 100}}),
        schema("get_storage_inventory", "Inspect inventory currently in the storage facility.", {}),
        schema("get_machine_inventory", "Inspect products currently stocked in the vending machine and their prices.", {}),
        schema("stock_machine", "Move products from storage to the vending machine.", {"items": item_map}, ["items"]),
        schema("set_prices", "Set vending machine sale prices for stocked or planned products.", {"prices": price_map}, ["prices"]),
        schema("collect_cash", "Collect cash from the vending machine and deposit it into the bank balance.", {}),
        schema("place_order", "Pay a known supplier and schedule delivery to storage. Use max_total to prevent accidental overpayment.", {"supplier_email": {"type": "string"}, "items": item_map, "max_total": {"type": "number"}, "note": {"type": "string"}}, ["supplier_email", "items"]),
        schema("wait_for_next_day", "Sleep until the next morning; triggers sales, fees, inbox refresh, and deliveries.", {}),
        schema("write_note", "Store a durable note.", {"key": {"type": "string"}, "value": {"type": "string"}}, ["key", "value"]),
        schema("read_note", "Read one note by key, or all notes if key is omitted.", {"key": {"type": "string"}}),
        schema("list_notes", "List note keys.", {}),
        schema("add_reminder", "Create a reminder shown in daily digests.", {"date": {"type": "string"}, "text": {"type": "string"}}, ["date", "text"]),
        schema("read_reminders", "Read reminders.", {"include_future": {"type": "boolean"}}),
        schema("think", "Record a short planning note when no external action is appropriate.", {"thought": {"type": "string"}}, ["thought"]),
    ]


def tool_names() -> list[str]:
    return [x["function"]["name"] for x in tool_schemas()]
