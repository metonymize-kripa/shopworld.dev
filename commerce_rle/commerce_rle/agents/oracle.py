"""
Oracle agents.

These are hand-written policies that solve each task type correctly. They are NOT
learning agents — they exist to prove the env is solvable and the reward maxes out
on a correct trajectory (an env that no oracle can fully solve has a bug in its
tests or its API). Use them as a fixed reference when wiring up a real RL policy:
a trained agent should approach the oracle's reward.
"""

from __future__ import annotations
from commerce_rle.env.commerce_env import CommerceEnv, StepResult


def _act(env: CommerceEnv, name: str, **args) -> StepResult:
    return env.step({"name": name, "args": args})


def oracle_cheapest_buy(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    # parse the keyword out of the instruction is brittle; instead search broadly.
    # the instruction names the keyword in quotes:
    instr = obs["instruction"]
    keyword = instr.split("'")[1]
    results = _act(env, "search_products", query=keyword, in_stock_only=True).observation["last_output"]
    cheapest = min(results, key=lambda p: p["price"])
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=cheapest["id"], qty=1,
         ship_address_id=addr["id"])
    return _act(env, "complete_task")


def oracle_cart_checkout(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    wanted = obs["context"]["wanted_product_ids"]
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    for pid in wanted:
        _act(env, "add_to_cart", user_id=uid, product_id=pid, qty=1)
    _act(env, "checkout_cart", user_id=uid, ship_address_id=addr["id"])
    return _act(env, "complete_task")


def oracle_return(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    oid = obs["context"]["order_id"]
    _act(env, "return_order", user_id=uid, order_id=oid)
    return _act(env, "complete_task")


def oracle_constrained_buy(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    min_rating = obs["context"]["min_rating"]
    keyword = obs["instruction"].split("'")[1]
    results = _act(env, "search_products", query=keyword, in_stock_only=True).observation["last_output"]
    eligible = [p for p in results if p["rating"] >= min_rating]
    target = min(eligible, key=lambda p: p["price"])
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=target["id"], qty=1,
         ship_address_id=addr["id"])
    return _act(env, "complete_task")


def oracle_budget_buy(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    budget = obs["context"]["budget"]
    keyword = obs["instruction"].split("'")[1]
    results = _act(env, "search_products", query=keyword, in_stock_only=True).observation["last_output"]
    affordable = [p for p in results if p["price"] <= budget]
    target = min(affordable, key=lambda p: p["price"])
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=target["id"], qty=1,
         ship_address_id=addr["id"])
    return _act(env, "complete_task")


def oracle_cart_edit(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    target = {int(k): v for k, v in obs["context"]["target"].items()}
    current = {c["product_id"]: c["qty"]
               for c in _act(env, "show_cart", user_id=uid).observation["last_output"]}
    # remove anything not in target
    for pid in list(current):
        if pid not in target:
            _act(env, "remove_from_cart", user_id=uid, product_id=pid)
    # set each target product to the right qty by removing then adding fresh
    for pid, qty in target.items():
        if pid in current:
            _act(env, "remove_from_cart", user_id=uid, product_id=pid)
        _act(env, "add_to_cart", user_id=uid, product_id=pid, qty=qty)
    return _act(env, "complete_task")


def oracle_reorder(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    orders = _act(env, "list_orders", user_id=uid).observation["last_output"]
    last = orders[-1]
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=last["product_id"], qty=1,
         ship_address_id=addr["id"])
    return _act(env, "complete_task")


def oracle_wishlist_buy(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    saved = _act(env, "show_wishlist", user_id=uid).observation["last_output"]
    pid = saved[0]["product_id"]
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=pid, qty=1, ship_address_id=addr["id"])
    return _act(env, "complete_task")


def oracle_refuse(env: CommerceEnv, obs: dict) -> StepResult:
    # the correct policy: search, find nothing valid, refuse without mutating.
    uid = obs["context"]["user_id"]
    keyword = obs["instruction"].split("'")[1]
    _act(env, "search_products", query=keyword, in_stock_only=True)  # read-only
    return _act(env, "complete_task", answer="no valid item available; not ordering")


def oracle_compound_buy_wish(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    buy_id = obs["context"]["buy_id"]
    save_id = obs["context"]["wishlist_id"]
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=buy_id, qty=1,
         ship_address_id=addr["id"])
    _act(env, "add_to_wishlist", user_id=uid, product_id=save_id)
    return _act(env, "complete_task")


def oracle_compound_return_rebuy(env: CommerceEnv, obs: dict) -> StepResult:
    uid = obs["context"]["user_id"]
    oid = obs["context"]["order_id"]
    repl_id = obs["context"]["replacement_id"]
    _act(env, "return_order", user_id=uid, order_id=oid)
    addr = _act(env, "default_address", user_id=uid).observation["last_output"]
    _act(env, "place_order", user_id=uid, product_id=repl_id, qty=1,
         ship_address_id=addr["id"])
    return _act(env, "complete_task")


# map task_id prefix -> oracle
def solve(env: CommerceEnv, obs: dict) -> StepResult:
    tid = env.task.task_id
    dispatch = [
        ("cheapest_buy", oracle_cheapest_buy),
        ("cart_checkout", oracle_cart_checkout),
        ("return_", oracle_return),
        ("constrained_buy", oracle_constrained_buy),
        ("budget_buy", oracle_budget_buy),
        ("cart_edit", oracle_cart_edit),
        ("reorder", oracle_reorder),
        ("wishlist_buy", oracle_wishlist_buy),
        ("refuse_", oracle_refuse),
        ("compound_buy_wish", oracle_compound_buy_wish),
        ("compound_return_rebuy", oracle_compound_return_rebuy),
    ]
    for prefix, fn in dispatch:
        if tid.startswith(prefix):
            return fn(env, obs)
    raise ValueError(f"no oracle for task {tid}")
