"""
Tests proving the three load-bearing eval ideas + env solvability.

Run: pytest -q   (from repo root)
"""

from __future__ import annotations
import random
import pytest

from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import (
    make_dataset, REGISTRY, REFUSAL_GENERATORS, sample_task,
)
from commerce_rle.agents import oracle


# ── 1. oracle solves every generator to full reward, zero collateral ─────────

@pytest.mark.parametrize("gen_name", list(REGISTRY))
def test_oracle_full_reward(gen_name):
    rng = random.Random(123)
    env = CommerceEnv()
    for _ in range(10):
        task = sample_task(rng, gen_name)
        obs = env.reset(task)
        result = oracle.solve(env, obs)
        assert result.done
        assert result.info["task_goal_complete"] or task.expects_refusal, result.info
        assert result.info["collateral_damage"] == [], result.info
        assert result.info["collateral_fields"] == [], result.info
        # full reward = 1.5 for both action tasks and clean refusals
        assert result.reward == pytest.approx(1.5), (gen_name, result.reward, result.info)
    env.close()


def test_all_twelve_generators_present():
    # coverage guard: the breadth we committed to must stay wired up
    expected = {
        "cheapest_in_stock_buy", "cart_checkout", "return_order",
        "constrained_buy", "budget_enforced_buy", "cart_edit_to_target",
        "reorder_last", "wishlist_to_cart", "refuse_out_of_stock",
        "refuse_over_budget", "compound_buy_and_wishlist",
        "compound_return_and_rebuy",
    }
    assert set(REGISTRY) == expected
    assert REFUSAL_GENERATORS <= set(REGISTRY)


def test_refusal_task_penalizes_acting():
    """On a refusal task, an agent that places an order must be penalized and
    score TGC=0, even though the order itself is a 'valid' API call."""
    env = CommerceEnv()
    # find a refuse_over_budget task and force a (technically affordable) action
    rng = random.Random(7)
    task = None
    for _ in range(50):
        cand = sample_task(rng, "refuse_out_of_stock")
        task = cand
        break
    obs = env.reset(task)
    uid = obs["context"]["user_id"]
    # buy SOME in-stock distractor (the wrong thing) — the refusal task forbids it
    products = env.step({"name": "search_products", "args": {"query": "", }}).observation["last_output"]
    in_stock = [p for p in products if p["stock"] > 0]
    assert in_stock, "test setup expects some in-stock distractor"
    env.step({"name": "place_order", "args": {
        "user_id": uid, "product_id": in_stock[0]["id"], "qty": 1, "ship_address_id": 10}})
    result = env.step({"name": "complete_task"})
    assert result.info["tgc"] == 0, result.info
    assert result.reward < 0, result.reward     # acting is punished
    env.close()


def test_refusal_task_rewards_inaction():
    env = CommerceEnv()
    rng = random.Random(8)
    task = sample_task(rng, "refuse_over_budget")
    obs = env.reset(task)
    # do nothing but declare completion
    result = env.step({"name": "complete_task"})
    assert result.info["tgc"] == 1, result.info
    assert result.reward == pytest.approx(1.5), result.reward
    env.close()


# ── 2. no-op trajectory scores ~0 and completes nothing ──────────────────────

def test_noop_scores_zero():
    env = CommerceEnv()
    task = make_dataset(1, seed=1, name="cheapest_in_stock_buy")[0]
    env.reset(task)
    result = env.step({"name": "complete_task"})
    assert result.done
    assert not result.info["task_goal_complete"]
    assert result.reward == pytest.approx(0.0)
    env.close()


# ── 3. collateral damage is detected and penalized ───────────────────────────

def test_collateral_damage_penalized():
    env = CommerceEnv()
    task = make_dataset(1, seed=2, name="cheapest_in_stock_buy")[0]
    obs = env.reset(task)
    uid = obs["context"]["user_id"]
    # solve correctly first
    keyword = obs["instruction"].split("'")[1]
    results = env.step({"name": "search_products",
                        "args": {"query": keyword, "in_stock_only": True}}).observation["last_output"]
    cheapest = min(results, key=lambda p: p["price"])
    env.step({"name": "place_order", "args": {
        "user_id": uid, "product_id": cheapest["id"], "qty": 1, "ship_address_id": 10}})
    # now scribble outside scope: wishlist is NOT in write_scope
    env.step({"name": "add_to_wishlist", "args": {"user_id": uid, "product_id": cheapest["id"]}})
    result = env.step({"name": "complete_task"})
    assert result.info["task_goal_complete"]              # goal still met
    assert "wishlist" in result.info["collateral_damage"] # but damage caught
    # reward = 1.0 work + 0.5 bonus - 0.75 damage = 0.75
    assert result.reward == pytest.approx(0.75), result.reward
    env.close()


# ── 4. no_op labels are auto-derived, not hand-set ───────────────────────────

def test_noop_labels_auto_derived():
    env = CommerceEnv()
    task = make_dataset(1, seed=3, name="cheapest_in_stock_buy")[0]
    env.reset(task)
    labels = {t.requirement: t.label for t in env.tests}
    # "real work" tests fail on an untouched DB -> no_op_fail
    work = [r for r, lbl in labels.items() if lbl == "no_op_fail"]
    assert len(work) >= 5, labels
    # the delta guard ("only stock changed") is vacuously true on an untouched
    # DB -> no_op_pass. It guards against collateral, it doesn't measure work.
    guards = [r for r, lbl in labels.items() if lbl == "no_op_pass"]
    assert any("only target product" in r for r in guards), labels
    env.close()


# ── 5. disallowed action is rejected, not crashed ────────────────────────────

def test_disallowed_action_safe():
    env = CommerceEnv()
    task = make_dataset(1, seed=4, name="return_order")[0]
    env.reset(task)
    result = env.step({"name": "venmo_send_money", "args": {"amount": 999}})
    assert not result.done
    assert "disallowed" in result.observation["last_output"]["error"]
    env.close()


# ── 6. bad arguments surface as observation, not exception ───────────────────

def test_bad_args_safe():
    env = CommerceEnv()
    task = make_dataset(1, seed=5, name="return_order")[0]
    env.reset(task)
    result = env.step({"name": "show_product", "args": {"product_id": 999999}})
    assert not result.done
    assert "error" in result.observation["last_output"]
    env.close()


# ── 7. AppWorld reward mode: binary, sparse ──────────────────────────────────

def test_appworld_reward_binary():
    env = CommerceEnv(reward_mode="appworld")
    task = make_dataset(1, seed=11, name="cheapest_in_stock_buy")[0]
    obs = env.reset(task)
    result = oracle.solve(env, obs)
    assert result.done
    # AppWorld reward is exactly 1.0 on a fully-correct solution
    assert result.reward == pytest.approx(1.0), result.reward
    assert result.info["tgc"] == 1
    env.close()


def test_appworld_reward_zero_on_partial():
    env = CommerceEnv(reward_mode="appworld")
    task = make_dataset(1, seed=12, name="cheapest_in_stock_buy")[0]
    obs = env.reset(task)
    uid = obs["context"]["user_id"]
    keyword = obs["instruction"].split("'")[1]
    results = env.step({"name": "search_products",
                        "args": {"query": keyword, "in_stock_only": True}}).observation["last_output"]
    cheapest = min(results, key=lambda p: p["price"])
    # place the order but to the WRONG (non-default) address -> default-address
    # test fails, so TGC fails, but the order/product/qty/stock tests still pass.
    env.step({"name": "place_order", "args": {
        "user_id": uid, "product_id": cheapest["id"], "qty": 1, "ship_address_id": 11}})
    result = env.step({"name": "complete_task"})
    # one requirement missed -> TGC fails -> AppWorld reward is 0.0 (no partial credit)
    assert result.reward == pytest.approx(0.0), result.reward
    assert result.info["tgc"] == 0
    # but sub-goal completion shows real partial progress (most tests passed)
    assert 0.0 < result.info["sub_goal_completion"] < 1.0, result.info
    env.close()


def test_appworld_reward_sparse_midstep():
    env = CommerceEnv(reward_mode="appworld")
    task = make_dataset(1, seed=13, name="return_order")[0]
    obs = env.reset(task)
    uid = obs["context"]["user_id"]
    oid = obs["context"]["order_id"]
    # a non-terminal step yields zero reward in appworld mode, even if it helps
    mid = env.step({"name": "return_order", "args": {"user_id": uid, "order_id": oid}})
    assert mid.reward == pytest.approx(0.0), mid.reward
    assert not mid.done
    # terminal completion then pays the full binary reward
    end = env.step({"name": "complete_task"})
    assert end.reward == pytest.approx(1.0), end.reward
    env.close()


# ── 8. Scenario Goal Completion aggregation ──────────────────────────────────

def test_sgc_all_or_nothing():
    from commerce_rle.env.evaluator import scenario_goal_completion, evaluate, snapshot
    from commerce_rle.tasks.generators import make_scenarios

    env = CommerceEnv(reward_mode="appworld")
    tasks = make_scenarios(1, variants_per_scenario=3, seed=21,
                          name="cheapest_in_stock_buy")
    # solve all three variants -> SGC == 1.0
    evals = []
    for t in tasks:
        obs = env.reset(t)
        oracle.solve(env, obs)
        evals.append(evaluate(env.tests, env.start_state, snapshot(env.conn),
                              write_scope=t.write_scope))
    assert scenario_goal_completion(evals) == pytest.approx(1.0)

    # now fail one variant (no-op it) -> whole scenario fails
    obs = env.reset(tasks[0])
    env.step({"name": "complete_task"})  # no-op the first variant
    failed = evaluate(env.tests, env.start_state, snapshot(env.conn),
                      write_scope=tasks[0].write_scope)
    evals_mixed = [failed] + evals[1:]
    assert scenario_goal_completion(evals_mixed) == pytest.approx(0.0)
    env.close()


# ── 9. Field-level (row-delta) collateral damage ─────────────────────────────

def test_field_level_collateral_damage():
    """The case table-level diffing misses: an in-scope TABLE mutated in an
    out-of-scope FIELD. cheapest_buy scopes products to products.stock only."""
    from commerce_rle.env.evaluator import evaluate, snapshot

    env = CommerceEnv()
    task = make_dataset(1, seed=31, name="cheapest_in_stock_buy")[0]
    obs = env.reset(task)
    uid = obs["context"]["user_id"]
    keyword = obs["instruction"].split("'")[1]
    results = env.step({"name": "search_products",
                        "args": {"query": keyword, "in_stock_only": True}}).observation["last_output"]
    cheapest = min(results, key=lambda p: p["price"])
    # solve correctly (this touches products.stock — allowed)
    env.step({"name": "place_order", "args": {
        "user_id": uid, "product_id": cheapest["id"], "qty": 1, "ship_address_id": 10}})
    # now tamper with an out-of-scope FIELD in the same in-scope table:
    env.conn.execute("UPDATE products SET price = price + 100 WHERE id = ?", (cheapest["id"],))
    env.conn.commit()

    ev = evaluate(env.tests, env.start_state, snapshot(env.conn),
                  write_scope=task.write_scope)
    d = ev.to_dict()
    # products table is NOT flagged as table-level collateral (it's field-scoped)
    assert "products" not in d["collateral_damage"], d
    # but the price field IS flagged as field-level collateral
    assert "products.price" in d["collateral_fields"], d
    # and the delta-guard unit test fails, so TGC drops
    assert ev.tgc is False, d
    env.close()


def test_delta_exposed_in_info():
    """The row/field delta is available to predicates and in the eval dict."""
    from commerce_rle.env.evaluator import evaluate, snapshot

    env = CommerceEnv()
    task = make_dataset(1, seed=32, name="return_order")[0]
    obs = env.reset(task)
    uid = obs["context"]["user_id"]
    oid = obs["context"]["order_id"]
    env.step({"name": "return_order", "args": {"user_id": uid, "order_id": oid}})
    ev = evaluate(env.tests, env.start_state, snapshot(env.conn),
                  write_scope=task.write_scope)
    d = ev.to_dict()
    # orders row was modified: status placed/delivered -> returned
    assert "orders" in d["delta"], d
    modified = d["delta"]["orders"]["modified"]
    assert any("status" in changes for changes in modified.values()), d
    env.close()
