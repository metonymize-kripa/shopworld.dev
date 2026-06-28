# commerce-rle Explainer

A bounded Amazon-commerce reinforcement learning environment. The agent's action
space is restricted to a small Amazon-like API — no Venmo, no Spotify, no Gmail.
The environment grades on **end state**, not trajectory, so any valid path to the
goal scores full marks.

---

## Prerequisites

Python ≥ 3.10. No third-party runtime dependencies (stdlib + sqlite3 only).
[`uv`](https://github.com/astral-sh/uv) is the recommended launcher.

```bash
# Install the package + dev deps (pytest) in one shot — no virtualenv needed
uv pip install -e ".[dev]"
```

---

## Repo map

```
commerce_rle/
├── env/
│   ├── schema.py        # SQLite schema (users, products, orders, cart, wishlist, addresses)
│   ├── evaluator.py     # state-diff, no-op labeling, collateral-damage, reward
│   └── commerce_env.py  # Gym-style reset / step / done
├── api/
│   └── amazon.py        # the full bounded action surface (+ optional FastAPI server)
├── tasks/
│   ├── task.py          # Task dataclass
│   └── generators.py    # 12 parametric task generators = training distribution
└── agents/
    └── oracle.py        # hand-written solvers used as reward ceiling
scripts/
├── demo.py              # run the oracle through every task family
└── benchmark.py         # print TGC / SGC / SubG (AppWorld metrics)
tests/
└── test_env.py          # 11 tests proving the three eval ideas + env solvability
```

---

## Run everything

```bash
# Tests — all should pass
uv run pytest -q

# Demo — oracle through all 12 task families, prints reward breakdown
uv run python scripts/demo.py

# Benchmark — AppWorld-style TGC / SGC / SubG report
uv run python scripts/benchmark.py
```

---

## Core concepts

### 1. The RL loop

```python
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import make_dataset

env = CommerceEnv(max_steps=30)          # default: shaped reward
for task in make_dataset(n=256, seed=0):
    obs = env.reset(task)
    done = False
    while not done:
        action = policy(obs)             # {"name": <api_method>, "args": {...}}
        result = env.step(action)
        obs, reward, done = result.observation, result.reward, result.done
env.close()
```

The terminal action is always `{"name": "complete_task", "args": {}}`. The
episode also ends when `max_steps` is reached (the final state is then graded).

### 2. Observation structure

`env.reset(task)` and `result.observation` both return:

```python
{
    "instruction": "Buy the cheapest in-stock 'earbuds'...",
    "context":     {"user_id": 100},          # structured facts the agent may use
    "last_output": {...},                      # API response from the previous step
    "step":        0,
    "max_steps":   30,
}
```

### 3. Action space

Actions are plain dicts. Every allowed name maps to an `AmazonAPI` method:

| Name | Type | What it does |
|------|------|--------------|
| `search_products` | read | keyword search, optional category + in-stock filter |
| `show_product` | read | single product by id |
| `list_addresses` | read | all shipping addresses for a user |
| `default_address` | read | the user's default address |
| `show_cart` | read | current cart contents |
| `list_orders` | read | order history |
| `show_wishlist` | read | saved wishlist items |
| `add_to_cart` | write | add qty of a product to the cart |
| `remove_from_cart` | write | remove a product from the cart |
| `place_order` | write | direct single-product buy (decrements stock, debits balance) |
| `checkout_cart` | write | convert all cart items to orders, empty cart |
| `return_order` | write | mark an order returned, restock the item |
| `add_to_wishlist` | write | save a product to the wishlist |

Unknown or out-of-scope API names (e.g. `venmo_send_money`) return an error
observation — the env never crashes.

### 4. Reward modes

Select at construction time:

```python
env = CommerceEnv(reward_mode="shaped")    # default — dense, for RL training
env = CommerceEnv(reward_mode="appworld")  # binary TGC, matches AppWorld leaderboard
```

**Shaped** (oracle ceiling = **+1.5**):

```
reward = (fraction of no_op_fail tests passed)    # real work toward the goal
       + 0.5  if task fully complete + committed  # completion bonus
       - 0.75 * (tables touched outside write_scope)  # table-level collateral
       - 0.40 * (fields touched outside write_scope)  # field-level collateral
```

**AppWorld** (binary):

```
reward = 1.0  iff every unit test passes, else 0.0
```
Intermediate steps return 0.0; the reward lands only at `complete_task` (or a
forced max-steps timeout).

### 5. Three evaluation ideas

**State-diff** — the evaluator snapshots the SQLite DB before and after, diffs
every table at the row and field level. Any valid sequence of API calls that
produces the correct end state scores full marks.

**No-op labeling** — each test predicate is auto-tagged by running it against
the untouched start state. Tests that fail on an untouched DB (`no_op_fail`)
measure real work; tests that pass (`no_op_pass`) are guards against collateral
damage. Labels are derived, never hand-set.

**Collateral damage** — `Task.write_scope` declares which tables a correct
solution may mutate. Two granularities:

```python
write_scope = {"orders", "products.stock"}
# "orders"          → the entire orders table is fair game
# "products.stock"  → ONLY the stock field of products may change
```

Touching anything outside the scope is penalized in the shaped reward and
reflected in `result.info["collateral_damage"]` / `result.info["collateral_fields"]`.

### 6. Task families

12 generators span the realistic commerce surface:

| Family key | What the agent must do |
|------------|------------------------|
| `cheapest_in_stock_buy` | search → find cheapest in-stock keyword match → buy |
| `cart_checkout` | add two items to cart → checkout |
| `return_order` | return a delivered order |
| `constrained_buy` | cheapest match that clears a minimum rating bar |
| `budget_enforced_buy` | cheapest affordable match (balance is real) |
| `cart_edit_to_target` | add/remove/qty-adjust to reach an exact cart state |
| `reorder_last` | read history → repurchase the last item |
| `wishlist_to_cart` | buy the item saved on the wishlist |
| `refuse_out_of_stock` | **refusal** — all matches OOS → do nothing |
| `refuse_over_budget` | **refusal** — all matches unaffordable → do nothing |
| `compound_buy_and_wishlist` | **multi-step** — buy one item, wishlist another |
| `compound_return_and_rebuy` | **multi-step** — return an order, buy a replacement |

Refusal tasks invert the reward: correctly doing nothing scores +1.5; any
mutation is penalized.

### 7. Dataset helpers

```python
from commerce_rle.tasks.generators import (
    make_dataset,
    make_scenarios,
    make_stratified_scenarios,
    sample_task,
    REGISTRY,
)

# Fixed dataset of n tasks (reproducible)
tasks = make_dataset(n=256, seed=0)

# Sample one specific task family
task = sample_task(rng, "return_order")

# Scenario-grouped tasks for SGC evaluation
tasks = make_scenarios(n_scenarios=10, variants_per_scenario=3, seed=0)

# Guaranteed coverage of all 12 families
tasks = make_stratified_scenarios(variants_per_scenario=3, scenarios_per_family=2)
```

### 8. AppWorld metrics

Three metrics match the AppWorld benchmark (Trivedi et al., ACL 2024):

- **TGC** (Task Goal Completion) — all unit tests pass; binary.
- **SGC** (Scenario Goal Completion) — all variants in a scenario pass; binary.
- **SubG** (Sub-Goal Completion) — fraction of unit tests passed; partial credit.

```python
from commerce_rle.env.evaluator import (
    evaluate, snapshot,
    scenario_goal_completion,
    aggregate_metrics,
)

# Grade a final state independent of reward mode
ev = evaluate(env.tests, env.start_state, snapshot(env.conn),
              write_scope=task.write_scope)
print(ev.tgc, ev.sub_goal_completion)

# Dataset-level rollup
metrics = aggregate_metrics(all_evals)  # {"tgc": ..., "sub_goal_completion": ..., "n": ...}
```

---

## Test examples

All examples below are runnable with `uv run python -c "..."`.

### Example 1 — Single episode with the oracle

```python
# uv run python -c "
import random
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import sample_task
from commerce_rle.agents import oracle

rng = random.Random(42)
env = CommerceEnv()
task = sample_task(rng, 'cheapest_in_stock_buy')
obs = env.reset(task)
print('Instruction:', obs['instruction'])
result = oracle.solve(env, obs)
print('Reward:', result.reward)           # 1.5
print('TGC:   ', result.info['tgc'])      # 1
print('Steps: ', result.info['steps'])
env.close()
# "
```

### Example 2 — Shaped reward with a partial (wrong-address) solution

```python
# uv run python -c "
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import make_dataset

env = CommerceEnv(reward_mode='shaped')
task = make_dataset(1, seed=0, name='cheapest_in_stock_buy')[0]
obs = env.reset(task)
uid = obs['context']['user_id']
keyword = obs['instruction'].split(\"'\")[1]

products = env.step({'name': 'search_products',
                     'args': {'query': keyword, 'in_stock_only': True}}).observation['last_output']
cheapest = min(products, key=lambda p: p['price'])
# ship to address 11 (NOT the default) — one test fails
env.step({'name': 'place_order',
          'args': {'user_id': uid, 'product_id': cheapest['id'],
                   'qty': 1, 'ship_address_id': 11}})
result = env.step({'name': 'complete_task'})
print('Reward:', result.reward)                      # < 1.5 (one test missed)
print('TGC:   ', result.info['tgc'])                 # 0
print('SubG:  ', result.info['sub_goal_completion']) # > 0 (most tests pass)
env.close()
# "
```

### Example 3 — AppWorld binary mode (correct vs. partial)

```python
# uv run python -c "
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import make_dataset
from commerce_rle.agents import oracle

env = CommerceEnv(reward_mode='appworld')
task = make_dataset(1, seed=7, name='return_order')[0]
obs = env.reset(task)

# Mid-step reward is 0 in appworld mode (sparse)
uid, oid = obs['context']['user_id'], obs['context']['order_id']
mid = env.step({'name': 'return_order', 'args': {'user_id': uid, 'order_id': oid}})
print('Mid-step reward:', mid.reward)   # 0.0

end = env.step({'name': 'complete_task'})
print('Terminal reward:', end.reward)   # 1.0
env.close()
# "
```

### Example 4 — Refusal task: do nothing to score full marks

```python
# uv run python -c "
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import sample_task
import random

env = CommerceEnv()
task = sample_task(random.Random(99), 'refuse_over_budget')
obs = env.reset(task)
print('Instruction:', obs['instruction'])
# Correct: just complete without acting
result = env.step({'name': 'complete_task'})
print('Reward:', result.reward)   # 1.5 — clean refusal
print('TGC:   ', result.info['tgc'])
env.close()
# "
```

### Example 5 — Collateral damage detection

```python
# uv run python -c "
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import make_dataset
from commerce_rle.agents import oracle

env = CommerceEnv()
task = make_dataset(1, seed=2, name='cheapest_in_stock_buy')[0]
obs = env.reset(task)
uid = obs['context']['user_id']
keyword = obs['instruction'].split(\"'\")[1]

products = env.step({'name': 'search_products',
                     'args': {'query': keyword, 'in_stock_only': True}}).observation['last_output']
cheapest = min(products, key=lambda p: p['price'])
env.step({'name': 'place_order',
          'args': {'user_id': uid, 'product_id': cheapest['id'],
                   'qty': 1, 'ship_address_id': 10}})
# Wishlist is NOT in write_scope — this is collateral damage
env.step({'name': 'add_to_wishlist',
          'args': {'user_id': uid, 'product_id': cheapest['id']}})
result = env.step({'name': 'complete_task'})
print('Goal met:        ', result.info['task_goal_complete'])  # True
print('Collateral tables:', result.info['collateral_damage'])  # ['wishlist']
print('Reward:           ', result.reward)  # 0.75 (1.0 + 0.5 - 0.75)
env.close()
# "
```

### Example 6 — Dataset + aggregate metrics

```python
# uv run python -c "
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.env.evaluator import evaluate, snapshot, aggregate_metrics
from commerce_rle.tasks.generators import make_dataset
from commerce_rle.agents import oracle

env = CommerceEnv(reward_mode='appworld')
tasks = make_dataset(n=24, seed=0)
all_evals = []
for task in tasks:
    obs = env.reset(task)
    oracle.solve(env, obs)
    ev = evaluate(env.tests, env.start_state, snapshot(env.conn),
                  write_scope=task.write_scope)
    all_evals.append(ev)
env.close()
print(aggregate_metrics(all_evals))
# {'tgc': 1.0, 'sub_goal_completion': 1.0, 'n': 24}
# "
```

---

## Extending the environment

**New task family** — add a generator `(rng: random.Random) -> Task` to
`commerce_rle/tasks/generators.py` and register it in `REGISTRY`.

**New API action** — add a method to `commerce_rle/api/amazon.py` (`AmazonAPI`)
and its name to `_ALLOWED_ACTIONS` in `commerce_rle/env/commerce_env.py`.

**HTTP / MCP serving** — install the serve extra and call `build_app`:

```bash
uv pip install -e ".[serve]"
```

```python
from commerce_rle.api.amazon import AmazonAPI, build_app
from commerce_rle.env.schema import new_connection, seed

conn = new_connection()
seed(conn, task.seed_rows)
app = build_app(lambda: AmazonAPI(conn))
# then: uvicorn app:app
```

**Verify a new task is correct** — before trusting any numbers, run the oracle
and confirm it still hits reward 1.5. A task the oracle can't fully solve has a
bug in its tests or API:

```bash
uv run pytest -q                         # all 11 tests must stay green
uv run python scripts/demo.py            # oracle should show +1.500 for every family
uv run python scripts/benchmark.py      # TGC / SGC / SubG should all be 1.000
```
