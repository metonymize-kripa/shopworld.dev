"""Core ShopWorld environment: deterministic RLE with reset/step loop."""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
from contextlib import contextmanager

from shopworld.common.datetime import SimulatedClock
from shopworld.common.serialization import StateSnapshot, state_diff
from shopworld.common.errors import ShopWorldError, SimulationError


@dataclass
class Observation:
    """Agent observation at a timestep."""
    
    step_number: int
    timestamp: datetime
    shopify_state: Dict[str, Any]      # Visible store state
    support_inbox: Dict[str, Any]      # Support tickets/messages
    alerts: List[Dict[str, Any]]       # Inventory warnings, etc.
    available_actions: List[str]       # Allowed tool names
    query_cost_remaining: int        # API budget left
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
        self.step_number: int = 0
        self.total_query_cost: int = 0
        self.granted_scopes: List[str] = []
        self.terminated: bool = False
        self.truncated: bool = False
        
        # Trace
        self.trace: List[TraceStep] = []
        self.initial_snapshot: Optional[StateSnapshot] = None
        
        # Actor simulators (set during reset)
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
        if seed is not None:
            random.seed(seed)
        
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
        
        # Initialize actor simulators
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
    
    def step(self, action: Action) -> Tuple[Observation, Dict[str, float], bool, bool, Dict[str, Any]]:
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
        """Evaluate episode outcome based on final state and trace.
        
        Returns evaluation result with task completion, collateral damage,
        policy violations, and business metrics.
        """
        if not self.task:
            return {"error": "No task defined for evaluation"}
        
        final_state = self._get_current_state()
        
        return {
            "episode_id": self.episode_id,
            "task_completion": self.task.evaluate_completion(final_state),
            "collateral_damage": self._check_collateral_damage(),
            "policy_violations": self._count_violations(),
            "business_metrics": self._compute_business_metrics(),
            "api_efficiency": self._compute_api_efficiency(),
            "trace_summary": self._summarize_trace(),
        }
    
    def get_trace(self) -> List[TraceStep]:
        """Return full episode trace for analysis."""
        return self.trace.copy()
    
    def _init_database(self, options: Dict[str, Any]) -> None:
        """Initialize SQLite database with commerce schema."""
        # Placeholder - will be implemented with SQLModel models
        from shopworld.apps.lib.db import init_database
        self.db = init_database()
        
        if self.task and hasattr(self.task, 'initial_db_records'):
            self._load_task_records(self.task.initial_db_records)
    
    def _init_simulators(self, seed: Optional[int]) -> None:
        """Initialize actor simulators."""
        # Placeholders - will import actual simulator classes
        self.customer_sim = None  # CustomerSimulator(seed=seed)
        self.supplier_sim = None  # SupplierSimulator(seed=seed)
        self.logistics_sim = None  # LogisticsSimulator(seed=seed)
        self.demand_sim = None  # DemandSimulator(seed=seed)
        self.ad_sim = None  # AdSimulator(seed=seed)
        self.policy_supervisor = None  # PolicySupervisor()
    
    def _execute_action(self, action: Action) -> None:
        """Execute agent action on the world."""
        # Route to appropriate app/tool
        # Track API cost
        cost = self._estimate_api_cost(action)
        self.total_query_cost += cost
        
        if self.total_query_cost > self.query_cost_budget:
            self.terminated = True
    
    def _check_policy(self, action: Action) -> List[str]:
        """Check action against granted scopes and merchant policy."""
        violations = []
        
        # Check scope permissions
        required_scope = self._get_required_scope(action.tool_name)
        if required_scope and required_scope not in self.granted_scopes:
            violations.append(f"SCOPE: Missing {required_scope} for {action.tool_name}")
        
        # Check policy supervisor
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
            metrics.get("margin_change", 0.0) +
            metrics.get("customer_satisfaction_delta", 0.0) * 0.1
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
        """Compute business outcome metrics from current state."""
        # Placeholder - will query DB for actual metrics
        return {
            "revenue": 0.0,
            "margin": 0.0,
            "cash_balance": 0.0,
            "customer_satisfaction": 0.0,
            "stockout_rate": 0.0,
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
            "avg_reward": sum(
                sum(s.reward_components.values()) for s in self.trace
            ) / len(self.trace),
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
        """Get serializable representation of current database state."""
        # Placeholder - will serialize DB records
        return {}
    
    def _get_shopify_state(self) -> Dict[str, Any]:
        """Get visible Shopify state for agent observation."""
        # Placeholder - will query relevant DB tables
        return {}
    
    def _get_support_state(self) -> Dict[str, Any]:
        """Get support inbox state."""
        # Placeholder
        return {"open_tickets": [], "unread_messages": 0}
    
    def _get_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts for agent."""
        # Placeholder
        return []
    
    def _get_available_actions(self) -> List[str]:
        """Get list of available tools based on granted scopes."""
        # Placeholder - will filter tools by scope
        return ["query_orders", "query_customers", "send_message"]
    
    def _get_required_scope(self, tool_name: str) -> Optional[str]:
        """Get required scope for a tool."""
        scope_map = {
            "query_orders": "read_orders",
            "query_customers": "read_customers",
            "update_order": "write_orders",
            "create_refund": "write_orders",
            "adjust_inventory": "write_inventory",
        }
        return scope_map.get(tool_name)
    
    def _estimate_api_cost(self, action: Action) -> int:
        """Estimate GraphQL cost points for an action."""
        # Placeholder - will implement Shopify-like cost model
        base_cost = 10
        if "bulk" in action.tool_name:
            base_cost = 50
        return base_cost
    
    def _create_support_ticket(self, event: Dict[str, Any]) -> None:
        """Create a support ticket from simulator event."""
        # Placeholder
        pass
    
    def _update_fulfillment(self, event: Dict[str, Any]) -> None:
        """Update fulfillment status from logistics event."""
        # Placeholder
        pass
    
    def _create_inventory_alert(self, event: Dict[str, Any]) -> None:
        """Create inventory alert."""
        # Placeholder
        pass
    
    def _load_task_records(self, records: List[Dict[str, Any]]) -> None:
        """Load initial DB records from task definition."""
        # Placeholder
        pass
