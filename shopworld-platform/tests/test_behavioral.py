"""Behavioral tests: state mutation, scope denial, WISMO end-to-end, determinism.

These tests verify that the environment does more than pass shape checks —
they assert real commerce state transitions, enforced policy boundaries, and
reproducible evaluation outcomes.
"""

import pytest

from shopworld.environment import ShopWorldEnv, Action
from shopworld.task import TaskLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wismo_task():
    """Load the bundled WISMO JSON task."""
    loader = TaskLoader()
    loader.load_all()
    task = loader.get_task("wismo-cooperative-10")
    assert task is not None, "wismo-cooperative-10 task not found"
    return task


@pytest.fixture
def wismo_env(wismo_task):
    env = ShopWorldEnv(task=wismo_task, enable_tracing=True, max_steps=20)
    env.reset(seed=42)
    return env


# ---------------------------------------------------------------------------
# P1 — Database seeding and state read-back
# ---------------------------------------------------------------------------

class TestDatabaseSeeding:
    """Verify that task initial_db_records are loaded and queryable."""

    def test_orders_seeded_from_task(self, wismo_env):
        state = wismo_env._get_current_state()
        order_ids = [o["id"] for o in state["orders"]]
        assert "order-wismo-001" in order_ids

    def test_customers_seeded_from_task(self, wismo_env):
        state = wismo_env._get_current_state()
        customer_ids = [c["id"] for c in state["customers"]]
        assert "customer-wismo-001" in customer_ids

    def test_support_ticket_seeded_from_task(self, wismo_env):
        state = wismo_env._get_current_state()
        ticket_ids = [t["id"] for t in state["support_tickets"]]
        assert "ticket-wismo-001" in ticket_ids

    def test_initial_snapshot_reflects_seeded_state(self, wismo_env):
        snap = wismo_env.initial_snapshot
        assert snap is not None
        assert "order-wismo-001" in [o["id"] for o in snap.database_state.get("orders", [])]

    def test_deterministic_seeding_same_state(self, wismo_task):
        """Two resets with the same seed produce identical initial states."""
        env1 = ShopWorldEnv(task=wismo_task)
        env2 = ShopWorldEnv(task=wismo_task)
        env1.reset(seed=42)
        env2.reset(seed=42)
        state1 = env1._get_current_state()
        state2 = env2._get_current_state()
        assert state1["orders"] == state2["orders"]
        assert state1["support_tickets"] == state2["support_tickets"]


# ---------------------------------------------------------------------------
# P1 — Scope enforcement via graphql_api scope registry
# ---------------------------------------------------------------------------

class TestScopeEnforcement:
    """Verify that tools blocked by missing scopes are recorded as violations."""

    def test_scope_violation_recorded_for_blocked_tool(self, wismo_task):
        """adjust_inventory needs write_inventory; WISMO task doesn't grant it."""
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True)
        env.reset(seed=42)

        action = Action(
            tool_name="adjust_inventory",
            arguments={"inventory_item_id": "x", "location_id": "y", "delta": 10},
        )
        _, _, _, _, info = env.step(action)
        assert len(info["violations"]) > 0
        assert any("SCOPE:" in v for v in info["violations"])

    def test_allowed_tool_has_no_violation(self, wismo_task):
        """query_orders is in the WISMO task's allowed_scopes."""
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True)
        env.reset(seed=42)

        action = Action(tool_name="query_orders", arguments={})
        _, _, _, _, info = env.step(action)
        assert info["violations"] == []

    def test_available_actions_filtered_by_scope(self, wismo_task):
        """Only tools whose scopes are granted should appear in available_actions."""
        env = ShopWorldEnv(task=wismo_task)
        obs, _ = env.reset(seed=42)
        assert "query_orders" in obs.available_actions
        assert "adjust_inventory" not in obs.available_actions

    def test_denied_action_does_not_mutate_state(self, wismo_task):
        """A scope-blocked action must not change the DB."""
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True)
        env.reset(seed=42)
        state_before = env._get_current_state()

        action = Action(
            tool_name="adjust_inventory",
            arguments={"inventory_item_id": "x", "location_id": "y", "delta": 10},
        )
        env.step(action)
        state_after = env._get_current_state()
        assert state_before["inventory_levels"] == state_after["inventory_levels"]


# ---------------------------------------------------------------------------
# P1 — Real state mutation via send_message
# ---------------------------------------------------------------------------

class TestStateMutation:
    """Verify that allowed actions actually mutate the database."""

    def test_send_message_creates_support_message(self, wismo_env):
        action = Action(
            tool_name="send_message",
            arguments={"ticket_id": "ticket-wismo-001"},
            message="Hi Casey, I'm looking into your order now.",
        )
        wismo_env.step(action)

        state = wismo_env._get_current_state()
        msgs = state.get("support_messages", [])
        agent_msgs = [m for m in msgs if m["ticket_id"] == "ticket-wismo-001" and m["sender_type"] == "AGENT"]
        assert len(agent_msgs) == 1
        assert "Casey" in agent_msgs[0]["body"]

    def test_close_ticket_updates_status(self, wismo_task):
        """close_ticket mutates ticket status to SOLVED in the DB."""
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True, max_steps=20)
        env.reset(seed=42)
        # close_ticket only (no send_message first, so task stays non-terminal)
        env.step(Action(
            tool_name="close_ticket",
            arguments={"ticket_id": "ticket-wismo-001"},
        ))

        state = env._get_current_state()
        ticket = next(t for t in state["support_tickets"] if t["id"] == "ticket-wismo-001")
        assert ticket["status"] == "SOLVED"

    def test_state_diff_detects_mutation(self, wismo_env):
        """state_diff between initial and post-action snapshots shows the change."""
        from shopworld.common.serialization import state_diff

        initial = wismo_env.initial_snapshot.database_state

        wismo_env.step(Action(
            tool_name="send_message",
            arguments={"ticket_id": "ticket-wismo-001"},
            message="We're on it!",
        ))
        final = wismo_env._get_current_state()

        diff = state_diff(initial, final)
        # A new support_message was added — diff should show it
        assert diff != {}


# ---------------------------------------------------------------------------
# P1 — WISMO end-to-end: reset → act → evaluate with real pass/fail
# ---------------------------------------------------------------------------

class TestWISMOEndToEnd:
    """Complete WISMO episode: agent responds → task evaluates as success."""

    def test_wismo_task_succeeds_after_reply(self, wismo_task):
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True, max_steps=20)
        env.reset(seed=42)

        # Agent looks up order (read-only)
        env.step(Action(tool_name="query_orders", arguments={}))

        # Agent replies to the customer
        env.step(Action(
            tool_name="send_message",
            arguments={"ticket_id": "ticket-wismo-001"},
            message="Hi Casey! Your order #1001 is being processed. We'll send tracking soon.",
        ))

        result = env.evaluate()

        task_block = result.get("task", {})
        assert task_block.get("success") is True, f"Task did not succeed: {task_block}"

    def test_wismo_task_fails_without_reply(self, wismo_task):
        """If agent never sends a message, the task should not be marked successful."""
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True, max_steps=5)
        env.reset(seed=42)

        # Only read — never reply
        for _ in range(3):
            env.step(Action(tool_name="query_orders", arguments={}))

        result = env.evaluate()
        task_block = result.get("task", {})
        assert task_block.get("success") is False, "Task should fail without a reply"

    def test_evaluation_contains_expected_keys(self, wismo_task):
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True, max_steps=5)
        env.reset(seed=42)
        env.step(Action(tool_name="query_orders", arguments={}))
        result = env.evaluate()

        for key in ("episode_id", "task", "safety", "business", "api", "overall"):
            assert key in result, f"Missing key in evaluation result: {key}"

    def test_scope_violation_penalizes_recommendation(self, wismo_task):
        """Attempting an out-of-scope action should lower the readiness recommendation."""
        env = ShopWorldEnv(task=wismo_task, enable_tracing=True, max_steps=20)
        env.reset(seed=42)

        # Violate scope deliberately
        for _ in range(3):
            env.step(Action(
                tool_name="adjust_inventory",
                arguments={"inventory_item_id": "x", "location_id": "y", "delta": 5},
            ))
        # Also reply so task can succeed
        env.step(Action(
            tool_name="send_message",
            arguments={"ticket_id": "ticket-wismo-001"},
            message="Your order is on its way!",
        ))

        result = env.evaluate()
        safety = result.get("safety", {})
        violations = safety.get("violations", {})
        assert violations.get("scope", 0) >= 3

        overall = result.get("overall", {})
        rec = overall.get("recommendation", "autonomous")
        assert rec != "autonomous", "Should not recommend autonomous after scope violations"


# ---------------------------------------------------------------------------
# P2 — graphql_api scope registry is the unified authority
# ---------------------------------------------------------------------------

class TestScopeRegistryUnification:
    """Verify env._TOOL_SCOPE_MAP entries map to real operations in OPERATION_SCOPES."""

    def test_all_tool_operations_in_scope_registry(self):
        from shopworld.apps.shopify_admin.graphql_api.scopes import OPERATION_SCOPES

        for tool, operation in ShopWorldEnv._TOOL_SCOPE_MAP.items():
            assert operation in OPERATION_SCOPES, (
                f"Tool '{tool}' maps to operation '{operation}' "
                f"which is not in OPERATION_SCOPES"
            )
