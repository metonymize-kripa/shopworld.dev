"""Task definitions and scenario loading for ShopWorld."""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from shopworld.common.errors import TaskError


@dataclass
class Task:
    """Single scenario/task for agent evaluation.
    
    A task defines:
    - Initial world state (products, orders, customers, hidden actor state)
    - Goal conditions (what constitutes success)
    - Allowed scopes (what permissions the agent has)
    - Evaluation criteria (state-based and trace-based checks)
    """
    
    id: str
    name: str
    description: str
    difficulty: int  # 1=Easy, 2=Medium, 3=Hard
    domain: str  # "support", "inventory", "fulfillment", "pricing", "composite"
    
    # Initial state
    initial_db_records: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    initial_hidden_state: Dict[str, Any] = field(default_factory=dict)
    
    # Permissions
    allowed_scopes: List[str] = field(default_factory=list)
    authority_level: str = "supervised"  # read-only, draft, supervised, bounded, autonomous
    
    # Success criteria
    success_conditions: List[Dict[str, Any]] = field(default_factory=list)
    failure_conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Evaluation
    evaluation_hooks: List[Callable] = field(default_factory=list)
    max_steps: Optional[int] = 100
    time_limit_hours: Optional[int] = None  # Simulated time limit
    
    # Events to inject during episode
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    
    def generate_initial_state(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate initial hidden state deterministically from seed."""
        if seed is not None:
            random.seed(seed)
        
        # Deep copy to avoid mutation
        import copy
        state = copy.deepcopy(self.initial_hidden_state)
        
        # Add any seed-derived randomization
        if "customer_satisfaction_noise" not in state:
            state["customer_satisfaction_noise"] = random.gauss(0, 0.1)
        
        return state
    
    def is_terminal(self, state: Dict[str, Any]) -> bool:
        """Check if episode has reached terminal state."""
        # Check success conditions
        for condition in self.success_conditions:
            if not self._check_condition(condition, state):
                return False
        return True
    
    def evaluate_completion(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate task completion based on final state."""
        results = {
            "task_id": self.id,
            "success": True,
            "passed_checks": [],
            "failed_checks": [],
            "partial_credit": 0.0,
        }
        
        # Check success conditions
        for condition in self.success_conditions:
            if self._check_condition(condition, final_state):
                results["passed_checks"].append(condition.get("description", "unnamed"))
            else:
                results["failed_checks"].append(condition.get("description", "unnamed"))
                results["success"] = False
        
        # Check failure conditions
        for condition in self.failure_conditions:
            if self._check_condition(condition, final_state):
                results["failed_checks"].append(f"FAILURE: {condition.get('description', 'unnamed')}")
                results["success"] = False
        
        # Compute partial credit
        total_checks = len(self.success_conditions)
        passed = len(results["passed_checks"])
        if total_checks > 0:
            results["partial_credit"] = passed / total_checks
        
        return results
    
    def compute_partial_reward(self, state: Dict[str, Any]) -> float:
        """Compute partial reward for intermediate steps."""
        # Count progress toward success conditions
        progress = 0.0
        for condition in self.success_conditions:
            if self._check_condition(condition, state):
                progress += 1.0
        
        return progress / max(len(self.success_conditions), 1)
    
    def _check_condition(self, condition: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """Check if a single condition is satisfied in state."""
        check_type = condition.get("type", "exists")
        
        if check_type == "exists":
            # Check if record exists matching criteria
            table = condition.get("table")
            filters = condition.get("filters", {})
            records = state.get(table, [])
            return any(
                all(r.get(k) == v for k, v in filters.items())
                for r in records
            )
        
        elif check_type == "field_equals":
            # Check specific field value
            table = condition.get("table")
            record_id = condition.get("id")
            field = condition.get("field")
            expected = condition.get("value")
            
            records = state.get(table, [])
            for r in records:
                if r.get("id") == record_id and r.get(field) == expected:
                    return True
            return False
        
        elif check_type == "count":
            # Check count of matching records
            table = condition.get("table")
            filters = condition.get("filters", {})
            min_count = condition.get("min", 0)
            max_count = condition.get("max", float('inf'))
            
            records = state.get(table, [])
            matching = [
                r for r in records
                if all(r.get(k) == v for k, v in filters.items())
            ]
            return min_count <= len(matching) <= max_count
        
        elif check_type == "custom":
            # Custom check via lambda (not serializable, for code-defined tasks)
            check_fn = condition.get("check_fn")
            if check_fn:
                return check_fn(state)
            return False
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "domain": self.domain,
            "allowed_scopes": self.allowed_scopes,
            "authority_level": self.authority_level,
            "max_steps": self.max_steps,
            "tags": self.tags,
        }


class TaskLoader:
    """Load and manage task library."""
    
    def __init__(self, tasks_dir: Optional[Path] = None):
        self.tasks_dir = tasks_dir or Path(__file__).parent / "tasks"
        self.tasks: Dict[str, Task] = {}
        self.scenarios: Dict[str, List[str]] = {}  # scenario_name -> task_ids
    
    def load_all(self) -> None:
        """Load all tasks from tasks directory."""
        if not self.tasks_dir.exists():
            return
        
        for task_file in self.tasks_dir.glob("*.json"):
            try:
                with open(task_file) as f:
                    data = json.load(f)
                task = self._parse_task(data)
                self.tasks[task.id] = task
            except Exception as e:
                raise TaskError(f"Failed to load {task_file}: {e}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_domain(self, domain: str) -> List[Task]:
        """Get all tasks in a domain."""
        return [t for t in self.tasks.values() if t.domain == domain]
    
    def get_tasks_by_difficulty(self, difficulty: int) -> List[Task]:
        """Get all tasks at a difficulty level."""
        return [t for t in self.tasks.values() if t.difficulty == difficulty]
    
    def get_tasks_by_tags(self, tags: List[str]) -> List[Task]:
        """Get tasks matching any of the given tags."""
        return [
            t for t in self.tasks.values()
            if any(tag in t.tags for tag in tags)
        ]
    
    def get_scenario_tasks(self, scenario_name: str) -> List[Task]:
        """Get all tasks in a scenario (related task variants)."""
        task_ids = self.scenarios.get(scenario_name, [])
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]
    
    def _parse_task(self, data: Dict[str, Any]) -> Task:
        """Parse task from JSON data."""
        return Task(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            difficulty=data.get("difficulty", 1),
            domain=data.get("domain", "general"),
            initial_db_records=data.get("initial_db_records", {}),
            initial_hidden_state=data.get("initial_hidden_state", {}),
            allowed_scopes=data.get("allowed_scopes", []),
            authority_level=data.get("authority_level", "supervised"),
            success_conditions=data.get("success_conditions", []),
            failure_conditions=data.get("failure_conditions", []),
            max_steps=data.get("max_steps", 100),
            scheduled_events=data.get("scheduled_events", []),
            tags=data.get("tags", []),
        )
    
    def create_curriculum(
        self,
        start_difficulty: int = 1,
        end_difficulty: int = 3,
        tasks_per_level: int = 10,
    ) -> List[Task]:
        """Create a difficulty-graded curriculum."""
        curriculum = []
        for diff in range(start_difficulty, end_difficulty + 1):
            tasks = self.get_tasks_by_difficulty(diff)
            # Random sample or specific selection
            selected = tasks[:tasks_per_level]
            curriculum.extend(selected)
        return curriculum


# Predefined task templates

SUPPORT_TASK_TEMPLATE = {
    "domain": "support",
    "allowed_scopes": [
        "read_orders",
        "read_customers",
        "write_orders",  # For refunds
    ],
    "success_conditions": [
        {
            "type": "exists",
            "table": "support_tickets",
            "filters": {"status": "resolved"},
            "description": "Customer complaint resolved",
        },
    ],
    "tags": ["support", "customer_service"],
}

INVENTORY_TASK_TEMPLATE = {
    "domain": "inventory",
    "allowed_scopes": [
        "read_products",
        "read_inventory",
        "write_inventory",
    ],
    "success_conditions": [
        {
            "type": "field_equals",
            "table": "inventory_levels",
            "field": "available",
            "description": "Inventory adjusted correctly",
        },
    ],
    "tags": ["inventory", "stock"],
}

FULFILLMENT_TASK_TEMPLATE = {
    "domain": "fulfillment",
    "allowed_scopes": [
        "read_orders",
        "read_fulfillments",
        "write_fulfillments",
    ],
    "success_conditions": [
        {
            "type": "field_equals",
            "table": "fulfillments",
            "field": "status",
            "value": "fulfilled",
            "description": "Order fulfilled",
        },
    ],
    "tags": ["fulfillment", "shipping"],
}


class TaskGenerator:
    """Generate task variants and counterfactuals."""
    
    def __init__(self, base_task: Task):
        self.base_task = base_task
    
    def generate_counterfactuals(self) -> List[Task]:
        """Generate counterfactual variants of a task."""
        variants = []
        
        # Same demand, lower cash
        low_cash = self._variant_with_cash_modifier(0.5)
        variants.append(low_cash)
        
        # Same supplier, longer lead time
        long_lead = self._variant_with_lead_time_multiplier(2.0)
        variants.append(long_lead)
        
        # Same complaint, VIP customer
        vip = self._variant_with_customer_type("vip")
        variants.append(vip)
        
        return variants
    
    def _variant_with_cash_modifier(self, modifier: float) -> Task:
        """Create variant with modified cash position."""
        import copy
        variant = copy.deepcopy(self.base_task)
        variant.id = f"{self.base_task.id}_cash_{modifier}"
        variant.name = f"{self.base_task.name} (Low Cash)"
        
        # Modify hidden state
        if "cash_balance" in variant.initial_hidden_state:
            variant.initial_hidden_state["cash_balance"] *= modifier
        
        variant.tags.append("counterfactual")
        variant.tags.append("cash_constraint")
        return variant
    
    def _variant_with_lead_time_multiplier(self, multiplier: float) -> Task:
        """Create variant with longer supplier lead times."""
        import copy
        variant = copy.deepcopy(self.base_task)
        variant.id = f"{self.base_task.id}_lead_{multiplier}"
        variant.name = f"{self.base_task.name} (Slow Supplier)"
        
        if "supplier_lead_time" in variant.initial_hidden_state:
            variant.initial_hidden_state["supplier_lead_time"] *= multiplier
        
        variant.tags.append("counterfactual")
        variant.tags.append("supplier_delay")
        return variant
    
    def _variant_with_customer_type(self, customer_type: str) -> Task:
        """Create variant with different customer type."""
        import copy
        variant = copy.deepcopy(self.base_task)
        variant.id = f"{self.base_task.id}_{customer_type}"
        variant.name = f"{self.base_task.name} ({customer_type.upper()})"
        
        variant.initial_hidden_state["customer_type"] = customer_type
        if customer_type == "vip":
            variant.initial_hidden_state["customer_lifetime_value"] = 5000.0
            variant.initial_hidden_state["escalation_risk"] = 0.8
        
        variant.tags.append("counterfactual")
        variant.tags.append(customer_type)
        return variant
