"""Core ShopWorld environment: deterministic RLE with reset/step loop."""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from shopworld.common.datetime import SimulatedClock
from shopworld.common.serialization import StateSnapshot, state_diff
from shopworld.common.errors import ShopWorldError
from shopworld.backend.db import init_database
from shopworld.api_surface import MERCHANT_TOOL_AUTHORIZATIONS
from shopworld.apps.shopify_admin.graphql_api.scopes import check_scope, ScopeError


@dataclass
class Observation:
    """Agent observation at a timestep."""

    step_number: int
    timestamp: datetime
    shopify_state: Dict[str, Any]  # Visible store state
    support_inbox: Dict[str, Any]  # Support tickets/messages
    alerts: List[Dict[str, Any]]  # Inventory warnings, etc.
    available_actions: List[str]  # Allowed tool names
    query_cost_remaining: int  # API budget left
    terminated: bool = False
    truncated: bool = False
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """Agent action."""

    tool_name: str
    arguments: Dict[str, Any]
    message: Optional[str] = None  # For support replies


@dataclass
class TraceStep:
    """Single step in episode trace."""

    step_number: int
    timestamp: datetime
    observation: Observation
    action: Action
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    reward_components: Dict[str, float]
    policy_violations: List[str]


class ShopWorldEnv:
    """Deterministic reinforcement learning environment for Shopify merchant agents.

    The environment simulates a Shopify store with:
    - Products, variants, inventory, orders, customers
    - Support inbox with simulated customers
    - Suppliers, logistics, advertising venues
    - Merchant policy constraints

    Key properties:
    - Deterministic: Same seed produces identical episodes
    - Resettable: Can snapshot/restore state for training
    - Observable: Agents see shopify state + support tickets
    - Evaluable: State-based and trace-based grading

    Usage:
        env = ShopWorldEnv(task=task)
        obs, info = env.reset(seed=42)
        done = False
        while not done:
            action = agent.decide(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
        result = env.evaluate()
    """

    # Maps tool names to their governing GraphQL operation name (for scope checks)
    _TOOL_SCOPE_MAP: Dict[str, str] = {
        "query_orders": "orders",
        "query_customers": "customers",
        "query_products": "products",
        "query_inventory": "inventoryLevels",
        "query_fulfillments": "fulfillmentOrders",
        "update_order": "orderUpdate",
        "create_refund": "refundCreate",
        "adjust_inventory": "inventoryAdjustQuantities",
        "send_message": "orderUpdate",  # requires write_orders
        "close_ticket": "orderUpdate",
        **{
            tool_name: authorization.operation
            for tool_name, authorization in MERCHANT_TOOL_AUTHORIZATIONS.items()
        },
    }

    def __init__(
        self,
        task: Optional[Any] = None,
        enable_tracing: bool = True,
        max_steps: Optional[int] = None,
        query_cost_budget: int = 10000,
    ):
        self.task = task
        self.enable_tracing = enable_tracing
        self.max_steps = max_steps
        self.query_cost_budget = query_cost_budget

        # Core components (initialized in reset)
        self.clock: Optional[SimulatedClock] = None
        self.db: Optional[Any] = None  # SQLModel session
        self.hidden_state: Dict[str, Any] = {}

        # Episode state
        self.episode_id: str = ""
        self.seed: Optional[int] = None
        self.rng: Optional[Any] = None
        self.step_number: int = 0
        self.total_query_cost: int = 0
        self.granted_scopes: List[str] = []
        self.terminated: bool = False
        self.truncated: bool = False

        # Trace
        self.trace: List[TraceStep] = []
        self.initial_snapshot: Optional[StateSnapshot] = None

        # Agent-visible API facade and actor simulators (set during reset)
        self.api_surface: Optional[Any] = None
        self.customer_sim: Optional[Any] = None
        self.supplier_sim: Optional[Any] = None
        self.logistics_sim: Optional[Any] = None
        self.demand_sim: Optional[Any] = None
        self.ad_sim: Optional[Any] = None
        self.policy_supervisor: Optional[Any] = None

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Observation, Dict[str, Any]]:
        """Reset environment to initial state for a new episode.

        Args:
            seed: Random seed for deterministic world generation
            options: Additional options (e.g., task variant, authority level)

        Returns:
            Initial observation and info dict
        """
        import random

        # Episode-local RNG. Never mutate global random state (determinism C2):
        # unrelated code consuming the global module must not perturb replays.
        self.seed = seed
        self.rng = random.Random(seed)

        self.episode_id = str(uuid.uuid4())[:8]
        self.step_number = 0
        self.total_query_cost = 0
        self.terminated = False
        self.truncated = False
        self.trace = []

        options = options or {}

        # Initialize simulated clock
        start_time = options.get("start_time")
        step_hours = options.get("step_hours", 1)
        self.clock = SimulatedClock(start_time=start_time, step_size_hours=step_hours)

        # Load task initial state if provided
        if self.task:
            self.hidden_state = self.task.generate_initial_state(seed=seed)
            self.granted_scopes = self.task.allowed_scopes
        else:
            self.hidden_state = {}
            self.granted_scopes = options.get("scopes", ["read_orders", "read_customers"])

        # Initialize database with task-specific seed data
        self._init_database(options)

        # Initialize agent-visible API facade and actor simulators
        self._init_api_surface()
        self._init_simulators(seed)

        # Create initial state snapshot for reset/restore
        if self.enable_tracing:
            self.initial_snapshot = self._create_snapshot()

        # Generate initial observation
        obs = self._create_observation()
        info = {
            "episode_id": self.episode_id,
            "granted_scopes": self.granted_scopes,
            "task_id": self.task.id if self.task else None,
        }

        return obs, info

    def step(
        self, action: Action
    ) -> Tuple[Observation, Dict[str, float], bool, bool, Dict[str, Any]]:
        """Execute one agent action and advance world state.

        Args:
            action: Agent action (tool call or message)

        Returns:
            observation, reward_vector, terminated, truncated, info
        """
        if self.terminated or self.truncated:
            raise ShopWorldError("Episode already ended. Call reset() first.")

        # Capture state before action
        state_before = self._get_current_state()

        # Validate action against granted scopes
        violations = self._check_policy(action)

        # Execute action if no scope violations
        if not any(v.startswith("SCOPE:") for v in violations):
            self._execute_action(action)

        # Advance simulated time
        self.clock.step()
        self.step_number += 1

        # Run actor simulators to generate exogenous events
        self._run_simulators()

        # Check for episode termination conditions
        self._check_termination()

        # Check truncation (max steps)
        if self.max_steps and self.step_number >= self.max_steps:
            self.truncated = True

        # Create observation
        obs = self._create_observation()

        # Compute reward components
        reward = self._compute_reward(action, violations)

        # Record trace step
        if self.enable_tracing:
            state_after = self._get_current_state()
            trace_step = TraceStep(
                step_number=self.step_number,
                timestamp=self.clock.now(),
                observation=obs,
                action=action,
                state_before=state_before,
                state_after=state_after,
                reward_components=reward,
                policy_violations=violations,
            )
            self.trace.append(trace_step)

        info = {
            "step_number": self.step_number,
            "query_cost_used": self.total_query_cost,
            "violations": violations,
        }

        return obs, reward, self.terminated, self.truncated, info

    def save_state(self) -> StateSnapshot:
        """Create snapshot of current state for restore."""
        return self._create_snapshot()

    def load_state(self, snapshot: StateSnapshot) -> None:
        """Restore environment to saved state."""
        self.episode_id = snapshot.episode_id
        self.step_number = snapshot.step_number
        # Restore clock, DB, hidden state from snapshot
        # (implementation depends on serialization format)

    def evaluate(self) -> Dict[str, Any]:
        """Evaluate episode outcome using the canonical Evaluator."""
        if not self.task:
            return {"error": "No task defined for evaluation"}

        from shopworld.evaluator import Evaluator

        initial_state = self.initial_snapshot.database_state if self.initial_snapshot else {}
        final_state = self._get_current_state()

        evaluator = Evaluator()
        result = evaluator.evaluate(
            task=self.task,
            trace=self.trace,
            initial_state=initial_state,
            final_state=final_state,
        )

        return {
            "episode_id": self.episode_id,
            **result.to_dict(),
            "api_efficiency": self._compute_api_efficiency(),
            "trace_summary": self._summarize_trace(),
        }

    def get_trace(self) -> List[TraceStep]:
        """Return full episode trace for analysis."""
        return self.trace.copy()

    def _init_database(self, options: Dict[str, Any]) -> None:
        """Initialize SQLite database with commerce schema."""
        db_path = options.get("database", ":memory:")
        self.db = init_database(db_path)

        if self.task and hasattr(self.task, "initial_db_records"):
            self._load_task_records(self.task.initial_db_records)

    def _det_id(self, n: int = 10) -> str:
        """Deterministic hex id from the episode RNG (for replayable records)."""
        rng = self.rng
        if rng is None:
            import uuid as _uuid

            return _uuid.uuid4().hex[:n]
        return "".join(rng.choice("0123456789abcdef") for _ in range(n))

    def _init_api_surface(self) -> None:
        """Initialize the constrained Merchant API Surface facade."""
        from shopworld.api_surface import MerchantAPISurface

        self.api_surface = (
            MerchantAPISurface(self.db, id_factory=self._det_id) if self.db else None
        )

    def _init_simulators(self, seed: Optional[int]) -> None:
        """Initialize actor simulators.

        Customer, logistics, and supplier simulators are wired. Demand and ad
        simulators (README §7) are deferred to a later milestone and left as
        None; ``_run_simulators`` guards on presence so they no-op safely.
        """
        from shopworld.apps.logistics.simulator import LogisticsSimulator
        from shopworld.apps.customers.simulator import CustomerSimulator
        from shopworld.apps.suppliers.simulator import SupplierSimulator

        self.logistics_sim = LogisticsSimulator(seed=seed)
        self.customer_sim = CustomerSimulator(seed=seed)
        self.supplier_sim = SupplierSimulator(seed=seed)
        self.demand_sim = None  # deferred (README §7)
        self.ad_sim = None  # deferred (README §7)
        self.policy_supervisor = None

    def _execute_action(self, action: Action) -> None:
        """Execute agent action on the world."""
        cost = self._estimate_api_cost(action)
        self.total_query_cost += cost

        if self.total_query_cost > self.query_cost_budget:
            self.terminated = True
            return

        if not self.db:
            return

        tool = action.tool_name
        args = action.arguments

        if self.api_surface and "." in tool:
            result = self.api_surface.call(tool, **args)
            self.hidden_state.setdefault("tool_results", []).append(
                {"step": self.step_number, "tool": tool, "result": result.to_dict()}
            )
            return

        if tool == "send_message":
            self._action_send_message(args, action.message)
        elif tool == "close_ticket":
            self._action_close_ticket(args)
        elif tool == "adjust_inventory":
            self._action_adjust_inventory(args)
        # query_* tools are read-only; no state change needed

    def _check_policy(self, action: Action) -> List[str]:
        """Check action against granted scopes (via graphql_api scope registry)."""
        violations = []

        operation = self._get_required_scope(action.tool_name)
        if operation:
            try:
                self._check_tool_scope(action.tool_name, set(self.granted_scopes))
            except ScopeError as exc:
                violations.append(f"SCOPE: {exc}")

        if self.policy_supervisor:
            policy_violations = self.policy_supervisor.check(action, self._get_current_state())
            violations.extend(policy_violations)

        return violations

    def _run_simulators(self) -> None:
        """Advance actor simulators and generate exogenous events."""
        # Run each simulator to update hidden state and generate events
        if self.customer_sim:
            events = self.customer_sim.step(self.clock.now(), self.hidden_state)
            self._process_events(events)

        if self.supplier_sim:
            events = self.supplier_sim.step(self.clock.now(), self.hidden_state)
            self._process_events(events)

        if self.logistics_sim:
            events = self.logistics_sim.step(self.clock.now(), self.hidden_state)
            self._process_events(events)

        if self.demand_sim:
            events = self.demand_sim.step(self.clock.now(), self.hidden_state)
            self._process_events(events)

    def _process_events(self, events: List[Dict[str, Any]]) -> None:
        """Process simulator-generated events (e.g., new support ticket)."""
        for event in events:
            if event["type"] == "support_ticket":
                self._create_support_ticket(event)
            elif event["type"] == "shipment_update":
                self._update_fulfillment(event)
            elif event["type"] == "inventory_alert":
                self._create_inventory_alert(event)

    def _create_observation(self) -> Observation:
        """Build agent observation from current world state."""
        return Observation(
            step_number=self.step_number,
            timestamp=self.clock.now(),
            shopify_state=self._get_shopify_state(),
            support_inbox=self._get_support_state(),
            alerts=self._get_alerts(),
            available_actions=self._get_available_actions(),
            query_cost_remaining=self.query_cost_budget - self.total_query_cost,
            terminated=self.terminated,
            truncated=self.truncated,
        )

    def _compute_reward(
        self,
        action: Action,
        violations: List[str],
    ) -> Dict[str, float]:
        """Compute multi-dimensional reward vector."""
        from shopworld.reward import RewardVector

        reward = RewardVector()

        # Task progress
        if self.task:
            reward.task_completion = self.task.compute_partial_reward(self._get_current_state())

        # Policy compliance
        reward.policy_compliance = -len(violations) * 10.0

        # API efficiency (penalize excessive queries)
        cost_ratio = self.total_query_cost / self.query_cost_budget
        reward.api_efficiency = -cost_ratio * 5.0

        # Business metrics (computed from state)
        metrics = self._compute_business_metrics()
        reward.business_outcome = (
            metrics.get("margin_change", 0.0)
            + metrics.get("customer_satisfaction_delta", 0.0) * 0.1
        )

        return reward.to_dict()

    def _check_termination(self) -> None:
        """Check if episode should terminate."""
        if self.task and self.task.is_terminal(self._get_current_state()):
            self.terminated = True

    def _check_collateral_damage(self) -> Dict[str, Any]:
        """Compare initial and final state for unauthorized changes."""
        if not self.initial_snapshot:
            return {"error": "No initial snapshot"}

        current = self._get_current_state()
        initial = self.initial_snapshot.database_state

        return state_diff(initial, current)

    def _count_violations(self) -> Dict[str, int]:
        """Count violations by type from trace."""
        counts = {"scope": 0, "policy": 0, "safety": 0}
        for step in self.trace:
            for v in step.policy_violations:
                if v.startswith("SCOPE:"):
                    counts["scope"] += 1
                elif v.startswith("POLICY:"):
                    counts["policy"] += 1
                elif v.startswith("SAFETY:"):
                    counts["safety"] += 1
        return counts

    def _compute_business_metrics(self) -> Dict[str, float]:
        """Compute business outcome metrics from current visible state.

        Derived from the serialized canonical state so the numbers are real, not
        placeholders. The richer trace-based business impact lives in
        ``Evaluator``; this is a lightweight current-state snapshot.
        """
        state = self._get_current_state()
        orders = state.get("orders", [])
        refunds = state.get("refunds", [])
        inventory = state.get("inventory_levels", [])
        revenue = sum(float(o.get("total_price", 0) or 0) for o in orders)
        refunded = sum(float(r.get("total_refunded", 0) or 0) for r in refunds)
        stockouts = sum(1 for lvl in inventory if (lvl.get("available", 0) or 0) <= 0)
        stockout_rate = stockouts / len(inventory) if inventory else 0.0
        return {
            "revenue": revenue,
            "margin": 0.0,  # requires COGS, not modeled in the MVP slice
            "cash_balance": revenue - refunded,
            "customer_satisfaction": 0.0,  # hidden-state driven; see simulators
            "stockout_rate": stockout_rate,
        }

    def _compute_api_efficiency(self) -> Dict[str, float]:
        """Compute API usage efficiency metrics."""
        return {
            "total_cost": self.total_query_cost,
            "budget_utilization": self.total_query_cost / self.query_cost_budget,
            "actions_per_step": len(self.trace) / max(self.step_number, 1),
        }

    def _summarize_trace(self) -> Dict[str, Any]:
        """Create summary statistics from episode trace."""
        if not self.trace:
            return {}

        return {
            "total_steps": len(self.trace),
            "total_violations": sum(len(s.policy_violations) for s in self.trace),
            "tool_usage": self._count_tool_usage(),
            "avg_reward": sum(sum(s.reward_components.values()) for s in self.trace)
            / len(self.trace),
        }

    def _count_tool_usage(self) -> Dict[str, int]:
        """Count how often each tool was used."""
        usage = {}
        for step in self.trace:
            tool = step.action.tool_name
            usage[tool] = usage.get(tool, 0) + 1
        return usage

    def _create_snapshot(self) -> StateSnapshot:
        """Create current state snapshot."""
        return StateSnapshot(
            episode_id=self.episode_id,
            step_number=self.step_number,
            timestamp=self.clock.now(),
            database_state=self._get_current_state(),
            hidden_state=self.hidden_state.copy(),
            clock_state={
                "current_time": self.clock.now().isoformat(),
                "step_count": self.clock.step_count,
            },
            metadata={
                "task_id": self.task.id if self.task else None,
                "granted_scopes": self.granted_scopes,
            },
        )

    def _get_current_state(self) -> Dict[str, Any]:
        """Get serializable snapshot of core database tables."""
        if not self.db:
            return {}

        from shopworld.apps.shopify_admin.models import (
            Order,
            Customer,
            SupportTicket,
            SupportMessage,
            InventoryLevel,
            Refund,
            Return,
        )
        from sqlmodel import select

        state: Dict[str, Any] = {}
        with self.db.session() as session:
            state["orders"] = [
                {
                    "id": r.id,
                    "name": r.name,
                    "display_fulfillment_status": r.display_fulfillment_status,
                    "display_financial_status": r.display_financial_status,
                    "total_price": float(r.total_price),
                    "customer_id": r.customer_id,
                }
                for r in session.exec(select(Order)).all()
            ]
            state["customers"] = [
                {"id": r.id, "email": r.email, "first_name": r.first_name, "last_name": r.last_name}
                for r in session.exec(select(Customer)).all()
            ]
            state["support_tickets"] = [
                {
                    "id": r.id,
                    "status": r.status,
                    "customer_id": r.customer_id,
                    "order_id": r.order_id,
                    "subject": r.subject,
                }
                for r in session.exec(select(SupportTicket)).all()
            ]
            state["support_messages"] = [
                {"id": r.id, "ticket_id": r.ticket_id, "sender_type": r.sender_type, "body": r.body}
                for r in session.exec(select(SupportMessage)).all()
            ]
            state["inventory_levels"] = [
                {
                    "inventory_item_id": r.inventory_item_id,
                    "location_id": r.location_id,
                    "available": r.available,
                }
                for r in session.exec(select(InventoryLevel)).all()
            ]
            state["refunds"] = [
                {
                    "id": r.id,
                    "order_id": r.order_id,
                    "total_refunded": float(r.total_refunded),
                    "reason": r.reason,
                }
                for r in session.exec(select(Refund)).all()
            ]
            state["returns"] = [
                {
                    "id": r.id,
                    "order_id": r.order_id,
                    "customer_id": r.customer_id,
                    "status": r.status,
                    "return_reason": r.return_reason,
                }
                for r in session.exec(select(Return)).all()
            ]
        return state

    def _get_shopify_state(self) -> Dict[str, Any]:
        """Get visible Shopify state for agent observation."""
        state = self._get_current_state()
        return {
            "orders": state.get("orders", []),
            "customers": state.get("customers", []),
            "inventory_levels": state.get("inventory_levels", []),
        }

    def _get_support_state(self) -> Dict[str, Any]:
        """Get support inbox state."""
        state = self._get_current_state()
        tickets = state.get("support_tickets", [])
        open_tickets = [t for t in tickets if t.get("status") == "OPEN"]
        messages = state.get("support_messages", [])
        return {
            "open_tickets": open_tickets,
            "unread_messages": len([m for m in messages if m.get("sender_type") == "CUSTOMER"]),
        }

    def _get_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts for agent (low-stock warnings etc.)."""
        alerts = []
        state = self._get_current_state()
        for level in state.get("inventory_levels", []):
            if level.get("available", 0) <= 0:
                alerts.append(
                    {
                        "type": "inventory_alert",
                        "severity": "warning",
                        "message": f"Out of stock: item {level['inventory_item_id']} at location {level['location_id']}",
                    }
                )
        return alerts

    def _get_available_actions(self) -> List[str]:
        """Return tools whose required scope is present in granted_scopes."""
        granted = set(self.granted_scopes)
        available = []
        for tool, operation in self._TOOL_SCOPE_MAP.items():
            try:
                self._check_tool_scope(tool, granted)
                available.append(tool)
            except ScopeError:
                pass
        return available

    def _check_tool_scope(self, tool_name: str, granted_scopes: set[str]) -> None:
        """Check exact Merchant API tool scopes, falling back to GraphQL operation scopes."""
        authorization = MERCHANT_TOOL_AUTHORIZATIONS.get(tool_name)
        if authorization is None:
            operation = self._get_required_scope(tool_name)
            if operation:
                check_scope(operation, granted_scopes)
            return

        required = authorization.required_scopes
        if not required or required & granted_scopes:
            return
        raise ScopeError(authorization.operation, required, granted_scopes)

    def _get_required_scope(self, tool_name: str) -> Optional[str]:
        """Return the GraphQL operation name that governs this tool's scope."""
        return self._TOOL_SCOPE_MAP.get(tool_name)

    def _estimate_api_cost(self, action: Action) -> int:
        """Estimate GraphQL cost points for an action."""
        # Placeholder - will implement Shopify-like cost model
        base_cost = 10
        if "bulk" in action.tool_name:
            base_cost = 50
        return base_cost

    def _create_support_ticket(self, event: Dict[str, Any]) -> None:
        """Create a support ticket from simulator event."""
        if not self.db:
            return
        from shopworld.apps.shopify_admin.models import SupportTicket

        with self.db.session() as session:
            ticket = SupportTicket(
                id=event.get("ticket_id") or f"ticket-{self._det_id(8)}",
                customer_id=event.get("customer_id"),
                order_id=event.get("order_id"),
                subject=event.get("subject", "Support request"),
                description=event.get("description"),
                category=event.get("category", "ORDER_ISSUE"),
                priority=event.get("priority", "MEDIUM"),
                status="OPEN",
            )
            session.add(ticket)
            session.commit()

    def _update_fulfillment(self, event: Dict[str, Any]) -> None:
        """Update fulfillment status from logistics event."""
        if not self.db:
            return
        from shopworld.apps.shopify_admin.models import Order
        from sqlmodel import select

        order_id = event.get("order_id")
        if not order_id:
            return
        with self.db.session() as session:
            order = session.exec(select(Order).where(Order.id == order_id)).first()
            if order:
                event_type = event.get("type")
                if event_type == "delivered":
                    order.display_fulfillment_status = "FULFILLED"
                elif event_type == "delivery_failed":
                    order.display_fulfillment_status = "PARTIAL"
                session.add(order)
                session.commit()

    def _create_inventory_alert(self, event: Dict[str, Any]) -> None:
        """Store inventory alert in hidden state for later retrieval."""
        self.hidden_state.setdefault("inventory_alerts", []).append(event)

    def _action_send_message(self, args: Dict[str, Any], message: Optional[str]) -> None:
        """Create a SupportMessage in response to a ticket."""
        if not self.db or not args.get("ticket_id"):
            return
        from shopworld.apps.shopify_admin.models import SupportMessage

        body = message or args.get("body", "")
        with self.db.session() as session:
            msg = SupportMessage(
                id=f"msg-{self._det_id(8)}",
                ticket_id=args["ticket_id"],
                sender_type="AGENT",
                body=body,
            )
            session.add(msg)
            session.commit()

    def _action_close_ticket(self, args: Dict[str, Any]) -> None:
        """Set a SupportTicket status to SOLVED."""
        if not self.db or not args.get("ticket_id"):
            return
        from shopworld.apps.shopify_admin.models import SupportTicket
        from sqlmodel import select

        with self.db.session() as session:
            ticket = session.exec(
                select(SupportTicket).where(SupportTicket.id == args["ticket_id"])
            ).first()
            if ticket:
                ticket.status = "SOLVED"
                session.add(ticket)
                session.commit()

    def _action_adjust_inventory(self, args: Dict[str, Any]) -> None:
        """Adjust inventory available quantity."""
        if not self.db:
            return
        from shopworld.apps.shopify_admin.models import InventoryLevel
        from sqlmodel import select

        item_id = args.get("inventory_item_id")
        location_id = args.get("location_id")
        delta = int(args.get("delta", 0))
        if not item_id or not location_id or delta == 0:
            return
        with self.db.session() as session:
            level = session.exec(
                select(InventoryLevel).where(
                    InventoryLevel.inventory_item_id == item_id,
                    InventoryLevel.location_id == location_id,
                )
            ).first()
            if level:
                level.available = max(0, level.available + delta)
                session.add(level)
                session.commit()

    def _load_task_records(self, records: Dict[str, List[Dict[str, Any]]]) -> None:
        """Load initial DB records from task definition into the database."""
        if not self.db or not records:
            return

        from shopworld.apps.shopify_admin.models import (
            Order,
            Customer,
            SupportTicket,
            InventoryItem,
            InventoryLevel,
            Location,
            Product,
            ProductVariant,
        )

        _model_map = {
            "orders": Order,
            "customers": Customer,
            "support_tickets": SupportTicket,
            "inventory_items": InventoryItem,
            "inventory_levels": InventoryLevel,
            "locations": Location,
            "products": Product,
            "product_variants": ProductVariant,
        }

        # Insertion order matters for FK constraints
        _ordered_tables = [
            "locations",
            "products",
            "product_variants",
            "inventory_items",
            "inventory_levels",
            "customers",
            "orders",
            "support_tickets",
        ]

        with self.db.session() as session:
            for table in _ordered_tables:
                model_cls = _model_map.get(table)
                if model_cls is None or table not in records:
                    continue
                for row in records[table]:
                    obj = model_cls.model_validate(row)
                    session.add(obj)
            # Also handle any extra tables not in the ordered list
            for table, rows in records.items():
                if table in _ordered_tables:
                    continue
                model_cls = _model_map.get(table)
                if model_cls is None:
                    continue
                for row in rows:
                    obj = model_cls.model_validate(row)
                    session.add(obj)
            session.commit()
