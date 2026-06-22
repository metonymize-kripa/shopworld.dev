"""Determinism and replay tests (README §13: determinism + trace replay)."""

import random

from shopworld.environment import Action, ShopWorldEnv
from shopworld.tasks import create_wismo_task, create_refund_task
from shopworld.traces import (
    ActionLog,
    extract_action_log,
    replay_episode,
    assert_deterministic,
)


def _wismo():
    return create_wismo_task(customer_type="cooperative", days_delayed=10, seed=42)


def _run_some_actions(env, ticket_id, order_id):
    env.step(Action("orders.query", {"id": order_id}))
    env.step(Action("tickets.reply", {"ticket_id": ticket_id, "body": "Looking into it now."}))


def test_same_seed_same_final_state():
    env1 = ShopWorldEnv(task=_wismo())
    env1.reset(seed=7)
    _run_some_actions(env1, "ticket-wismo-001", "order-1")

    env2 = ShopWorldEnv(task=_wismo())
    env2.reset(seed=7)
    _run_some_actions(env2, "ticket-wismo-001", "order-1")

    assert env1._get_current_state() == env2._get_current_state()


def test_reset_does_not_mutate_global_random():
    state_before = random.getstate()
    env = ShopWorldEnv(task=_wismo())
    env.reset(seed=123)
    env.step(Action("orders.query", {"id": "order-1"}))
    assert random.getstate() == state_before


def test_action_log_roundtrip_and_replay():
    env = ShopWorldEnv(task=_wismo())
    env.reset(seed=5)
    _run_some_actions(env, "ticket-wismo-001", "order-1")

    log = extract_action_log(env)
    assert log.seed == 5
    assert len(log.actions) == 2

    # JSON roundtrip
    log2 = ActionLog.from_json(log.to_json())
    assert log2.seed == log.seed
    assert log2.actions == log.actions

    replayed = replay_episode(_wismo(), log2)
    assert replayed._get_current_state() == env._get_current_state()


def test_assert_deterministic_helper():
    env = ShopWorldEnv(task=_wismo())
    env.reset(seed=99)
    _run_some_actions(env, "ticket-wismo-001", "order-1")
    log = extract_action_log(env)
    assert assert_deterministic(_wismo, log) is True


def test_refund_scenario_now_scorable():
    """Regression: refunds/returns must surface in state for scoring."""
    task = create_refund_task(days_since_delivery=3, fraud_risk=0.1, seed=42)
    env = ShopWorldEnv(task=task)
    obs, _ = env.reset(seed=1)
    state = env._get_current_state()
    assert "refunds" in state
    assert "returns" in state
