# commerce-rle

A bounded **Amazon-commerce reinforcement learning environment**. Built by stripping
the AppWorld benchmark down to a single app and rewriting the engine clean, while
keeping the three load-bearing ideas from AppWorld's evaluation harness:

1. **State-diff evaluation** — episodes are graded on the *end state* of the
   database, not the trajectory. Any valid path to the goal scores full marks.
2. **No-op test labeling** — every requirement is auto-tagged `no_op_fail`
   (fails on an untouched DB → measures real work) or `no_op_pass` (passes on an
   untouched DB → a guard against regressions). Labels are *derived* by running
   each test against the seeded start state, never hand-set.
3. **Collateral-damage checks** — after grading the goal, any table mutated
   outside the task's declared `write_scope` docks reward. The agent is penalized
   for buying the right thing the wrong way. Damage is detected at **two
   granularities** (see below): whole-table and individual row/field.

The agent's action space is bounded to the Amazon API and nothing else. There is
no Venmo/Spotify/Gmail surface — those routes don't exist, so a misfiring policy
physically cannot call them.

## Layout

```
commerce_rle/
├── env/
│   ├── evaluator.py     # state-diff, no-op labeling, collateral damage, reward
│   ├── schema.py        # canonical commerce DB schema + seeding
│   └── commerce_env.py  # Gym-style reset / step / done
├── api/
│   └── amazon.py        # the entire bounded action surface (+ optional FastAPI)
├── tasks/
│   ├── task.py          # Task dataclass (instruction, seed, tests, write_scope)
│   └── generators.py    # parametric task generators = the train distribution
└── agents/
    └── oracle.py        # hand-written solvers, used as a reward ceiling
scripts/demo.py          # roll the oracle, print reward breakdown
tests/test_env.py        # proves the three ideas + env solvability
```

## Quickstart

```bash
uv run pytest -q          # 8 tests, all green
uv run python scripts/demo.py
```

## The core loop

```python
from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import make_dataset

env = CommerceEnv(max_steps=30)
for task in make_dataset(n=256, seed=0):
    obs = env.reset(task)
    done = False
    while not done:
        action = policy(obs)                 # your RL policy
        result = env.step(action)            # {"name": "place_order", "args": {...}}
        obs, reward, done = result.observation, result.reward, result.done
```

Actions are `{"name": <api_method>, "args": {...}}`. The terminal action is
`{"name": "complete_task", "args": {"answer": <optional>}}`. Reward is dense:
shaped per-step from `evaluator.reward()`, with the completion bonus landing only
when the agent declares done.

## Reward shape

Two reward modes, chosen at env construction via `reward_mode`:

**`"shaped"` (default) — dense, for training.**

```
reward = (fraction of no_op_fail tests passed)      # real work toward goal
       + 0.5  if task_goal_complete and committed    # completion milestone
       - 0.75 * (tables touched outside write_scope)  # table-level collateral
       - 0.40 * (fields touched outside write_scope)  # field-level collateral
```

`no_op_pass` tests are never rewarded — passing them is the default; paying for
them would pay the agent for doing nothing. Oracle ceiling: **+1.5**.

**`"appworld"` — binary, AppWorld's native signal.**

```
reward = 1.0  iff every unit test passes (incl. guard tests), else 0.0
```

No partial credit, no separate damage term (damage that trips a guard test
already forces the reward to 0). Sparse: intermediate steps return 0.0; the full
reward lands only at `complete_task` (or on a forced `max_steps` timeout, which
grades the final state). Use this to report numbers comparable to the AppWorld
leaderboard, or to train against the true objective rather than a shaped proxy.

```python
env = CommerceEnv(reward_mode="appworld")   # binary TGC reward
env = CommerceEnv(reward_mode="shaped")     # dense shaped reward (default)
```

## State deltas (row & field level)

Evaluation works off a row-level diff of the database, mirroring AppWorld's
state-based unit tests rather than just checking which tables changed. For each
table the evaluator computes a `TableDelta`:

- `inserted` — `{pk: row}` present in the end state but not the start
- `deleted` — `{pk: row}` present in the start but not the end
- `modified` — `{pk: {field: (old, new)}}` for rows present in both that changed

This is exposed two ways. Predicates read it through the `EvalContext`:

```python
def t_only_stock_changed(ctx):
    for pk, changes in ctx.modified("products").items():
        assert pk == target_id, f"wrong product {pk} touched"
        assert set(changes) == {"stock"}, "only stock may change"
```

And it appears in `evaluation.to_dict()["delta"]` for logging and debugging.

**Field-level write scope.** `write_scope` accepts two granularities:

```python
write_scope = {"orders", "products.stock"}
```

`"orders"` allows any change to the orders table (coarse). `"products.stock"`
allows *only* the `stock` field of products to change — touching `price`,
`title`, or another product's row is **field-level collateral damage**, flagged
in `evaluation.collateral_fields` and penalized in the shaped reward. This catches
the case table-level diffing misses: an in-scope table mutated in an out-of-scope
field (e.g. an agent that correctly decrements stock but also rewrites the price).

Primary keys for the diff are registered from `schema.py:PRIMARY_KEYS` (all `id`
here; change in one place if a table uses a different key).

## AppWorld metrics

The evaluator exposes AppWorld's three benchmark metrics (Trivedi et al., ACL
2024) alongside the shaped reward:

- **TGC — Task Goal Completion.** `Evaluation.tgc`: True iff *all* unit tests
  pass. Binary, all-or-nothing. The headline AppWorld metric.
- **SGC — Scenario Goal Completion.** `scenario_goal_completion([evals])`: 1.0
  iff every task variant in a scenario gets TGC. A consistency metric — the same
  goal must hold under varied requirements and start states. Build scenario-
  grouped tasks with `make_scenarios(n, variants_per_scenario=3)`.
- **Sub-Goal Completion.** `Evaluation.sub_goal_completion`: fraction of unit
  tests passed. Partial credit, for tracking progress on tasks that don't fully
  solve.

```bash
uv run python scripts/benchmark.py    # runs the oracle, prints TGC / SGC / SubG
```

Aggregate across a dataset with `aggregate_metrics([evals])` for mean TGC and
sub-goal completion; group by `task.scenario_id` and average
`scenario_goal_completion` per group for SGC.

## Task families

Twelve generators span the realistic commerce surface (search→buy, filtering,
budget, cart, history, wishlist, returns, refusals, and multi-step compounds).
Each is `(rng) -> Task`: sample a world, set a goal, build state-diff tests from
the seeded start state. Registered in `tasks/generators.py:REGISTRY`.

| Family | What it exercises |
|--------|-------------------|
| `cheapest_in_stock_buy` | find & buy cheapest keyword match |
| `cart_checkout` | multi-item cart → checkout |
| `return_order` | return an existing delivered order |
| `constrained_buy` | cheapest match clearing a rating bar, with distractors |
| `budget_enforced_buy` | buy cheapest affordable item; balance is debited |
| `cart_edit_to_target` | add/remove/change-qty to reach an exact cart state |
| `reorder_last` | read order history, repurchase the last item |
| `wishlist_to_cart` | buy the item saved on the wishlist |
| `refuse_out_of_stock` | **refusal:** nothing in stock → do NOT order |
| `refuse_over_budget` | **refusal:** all matches unaffordable → do NOT order |
| `compound_buy_and_wishlist` | **multi-step:** buy one item, wishlist another |
| `compound_return_and_rebuy` | **multi-step:** return an order, buy a replacement |

`REFUSAL_GENERATORS` names the two whose correct behavior is to make no database
change. The oracle in `agents/oracle.py` solves every family to the +1.5 ceiling;
run `uv run python scripts/demo.py` to see each, or `uv run python scripts/benchmark.py` for
stratified TGC/SGC/SubG across all families.

### Refusal tasks (negative / "do nothing" tasks)

A commerce agent must sometimes decline — the item is out of stock, or everything
matching is over budget. For these the correct outcome is an **unchanged
database**. The evaluator handles this with `Task.expects_refusal=True`:

- **TGC** additionally requires `no_change` — any mutation fails the task, even a
  "valid" order, because acting at all was the error.
- **Reward** inverts: a clean refusal (no change + guard tests intact) scores the
  full +1.5; any mutation is penalized, scaling with how much was wrongly changed.

This closes a gap a naive reward would miss: without it, a no-action task has no
`no_op_fail` work tests, so the work fraction is degenerate (0/0) and the agent
would learn it can never profit by declining. See `reward()` and the `tgc`
property in `evaluator.py`.

## Extending

- **New task types** → add a generator to `tasks/generators.py` and register it
  in `REGISTRY`. A generator is `(rng) -> Task`: sample a world, set a goal, build
  the state-diff tests from the seeded start state.
- **New APIs** → add methods to `api/amazon.py` and the name to `_ALLOWED_ACTIONS`
  in `commerce_env.py`. Keep the surface commerce-only.
- **HTTP / MCP serving** → `api/amazon.py:build_app` exposes the API over FastAPI
  for containerized or cross-language agents. Install with `pip install -e ".[serve]"`.
- **Oracle ceiling** → before trusting a trained policy's numbers, confirm
  `agents/oracle.py` still hits reward 1.5 on your new tasks. An env no oracle can
  solve has a bug in its tests or API.

## Provenance

The evaluation *design* is borrowed from AppWorld (Trivedi et al., ACL 2024); none
of AppWorld's code or data is included. This is a clean reimplementation you can
fully inspect and reshape into a reward function — which the encrypted AppWorld
bundles do not allow.
