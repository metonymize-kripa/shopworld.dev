The useful AppWorld residue is the **deterministic stateful benchmark kernel**; discard the consumer-app world, benchmark data, leaderboard machinery, and most bundled/private content.

# Target Outcome

Build **ShopWorld** as an AppWorld-derived reinforcement learning environment where the agent is a **Shopify store owner AI** optimizing profit, cash, customer trust, and operational safety over simulated weeks.

AppWorld is valuable because it already proves the pattern:

1. Stateful app world.
2. Typed APIs.
3. Simulated users.
4. Task-specific initial states.
5. Programmatic evaluation.
6. Agent execution loop.
7. Logs and replay.

AppWorld’s repo states that each task is defined by **Supervisor**, **Instruction**, and **Initial State**, and the agent acts through APIs against a resettable world state. ([GitHub][1])

# Core to Keep

| Keep                        | AppWorld source area                  | Why it matters for Shopify RLE                                  |
| --------------------------- | ------------------------------------- | --------------------------------------------------------------- |
| `AppWorld` runtime pattern  | `src/appworld/environment.py`         | Resettable environment, action execution, logs, state snapshots |
| Task abstraction            | `src/appworld/task.py`                | Convert task into merchant objective / episode spec             |
| Evaluator abstraction       | `src/appworld/evaluator.py`           | Convert final DB state into score/reward                        |
| API docs substrate          | `src/appworld/api_docs.py`            | Agents need tool discovery and schemas                          |
| Request wrapper             | `src/appworld/requester.py`           | Useful if serving local APIs or MCP/HTTP                        |
| `common/` utilities         | `src/appworld/common`                 | Time, paths, IO, errors, safety guard, serialization            |
| `serve/`                    | `src/appworld/serve`                  | Remote rollouts, containerized agents, hosted training workers  |
| SQLModel/SQLite app pattern | `apps/lib/models/db` implied by guide | Deterministic commerce state with fast rollback                 |
| Minimal agent loop          | `experiments/code`                    | Starting scaffold for ReAct/tool/coding agents                  |
| Config generator pattern    | `experiments/configs`                 | Model/scaffold sweep infrastructure                             |
| App-generation guide ideas  | `guides/developing_new_apps.md`       | Recipe for new Shopify-like app modules                         |

AppWorld’s own guide confirms its app scaffold uses **FastAPI**, **Pydantic**, **SQLite**, and **SQLModel**, with each app containing `design.yaml`, `info.toml`, `models.py`, `factories.py`, `apis.py`, `responses.py`, tests, base DBs, API docs, and data generation scripts. ([GitHub][2])

# Delete / Ignore

| Delete / ignore                       | Reason                                                                               |
| ------------------------------------- | ------------------------------------------------------------------------------------ |
| `src/appworld/apps/*` consumer apps   | Replace Amazon/Spotify/etc. with Shopify Admin, suppliers, logistics, ads, customers |
| Existing benchmark task data          | Not Shopify-relevant                                                                 |
| Existing task generators              | Wrong objective space                                                                |
| Existing user/persona graph           | Replace with merchants, customers, suppliers, carriers, ad venues                    |
| Existing protected `.bundle` contents | Most app/task specifics are encrypted and domain-specific; not worth preserving      |
| `images/`                             | Documentation-only                                                                   |
| `notebooks/`                          | Useful for learning, not core runtime                                                |
| `leaderboard.py`                      | Defer until benchmark hardens                                                        |
| `download.py`                         | AppWorld-specific data plumbing                                                      |
| `install.py`                          | Bundle unpacking is not desirable for ShopWorld                                      |
| Most baseline experiment outputs      | Defer                                                                                |
| Existing 457 API surface              | Wrong tools, wrong ontology                                                          |

AppWorld explicitly says much of its released app/API/task implementation is stored in encrypted `.bundle` files, including app implementations, tests, data, and task generation. That makes a clean-room ShopWorld core preferable to trying to mine AppWorld’s protected app content. ([GitHub][1])

# Refactor Map

| AppWorld concept         | ShopWorld replacement                                                       |
| ------------------------ | --------------------------------------------------------------------------- |
| `AppWorld`               | `ShopWorld`                                                                 |
| Supervisor person        | Store owner / merchant principal                                            |
| Consumer apps            | Commerce operating systems                                                  |
| `apis.spotify.*` etc.    | `apis.shopify_admin.*`, `apis.supplier.*`, `apis.logistics.*`, `apis.ads.*` |
| Personal task            | Store operating objective                                                   |
| Initial personal app DBs | Initial store snapshot                                                      |
| Task completion          | End episode / submit operating report                                       |
| Evaluation tests         | Reward function + invariant checks                                          |
| User simulator           | Customers, browsers, suppliers, carriers, ad venues                         |
| Date/time reset          | Simulated commerce calendar                                                 |
| Collateral-damage checks | Policy, cash, SLA, trust, fraud, privacy, margin violations                 |

# New Minimal Repo

```text
shopworld/
  pyproject.toml
  README.md

  src/shopworld/
    __init__.py
    environment.py
    task.py
    evaluator.py
    reward.py
    requester.py
    api_docs.py

    common/
      datetime.py
      io.py
      paths.py
      safety_guard.py
      serialization.py
      errors.py

    apps/
      lib/
        db.py
        auth.py
        pagination.py
        ids.py
        graphql.py

      shopify_admin/
        design.yaml
        info.toml
        models.py
        factories.py
        apis.py
        responses.py
        schema.graphql

      suppliers/
        models.py
        apis.py
        simulator.py

      logistics/
        models.py
        apis.py
        simulator.py

      customers/
        models.py
        apis.py
        simulator.py

      ads/
        models.py
        apis.py
        simulator.py

      storefront/
        models.py
        apis.py
        simulator.py

    serve/
      http.py
      mcp.py

  generate/
    stores.py
    tasks.py
    scenarios.py
    counterfactuals.py

  experiments/
    agents/
      react_agent.py
      function_calling_agent.py
      policy_agent.py
    configs/
    run.py
    evaluate.py

  tests/
    test_shopify_admin.py
    test_scenarios.py
    test_reward.py
```

# First Deletion Pass

Use this if starting from a fork:

```bash
git clone https://github.com/StonyBrookNLP/appworld shopworld
cd shopworld
git checkout -b shopworld-core

rm -rf images notebooks scripts
rm -rf data
rm -rf src/appworld/apps
rm -rf generate/images
rm -rf generate/tasks
rm -rf experiments/prompts
rm -rf .github
rm -f src/appworld/download.py
rm -f src/appworld/install.py
rm -f src/appworld/leaderboard.py
rm -f README.pypi.md RELEASE_PROCESS.md
```

Then rename:

```bash
mv src/appworld src/shopworld
find . -type f -name "*.py" -exec sed -i '' 's/appworld/shopworld/g' {} +
find . -type f -name "*.md" -exec sed -i '' 's/AppWorld/ShopWorld/g' {} +
```

On Linux, replace `sed -i ''` with `sed -i`.

# Keep, But Simplify

| File / module            | Change                                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `environment.py`         | Rename `AppWorld` to `ShopWorld`; remove protected-data assumptions; preserve reset/execute/evaluate/logging |
| `task.py`                | Strip to `task_id`, `instruction`, `store_id`, `initial_state_path`, `episode_length`, `reward_spec`         |
| `evaluator.py`           | Convert from pass/fail tests to reward vector                                                                |
| `api_docs.py`            | Generate function-calling docs from GraphQL-like operations                                                  |
| `requester.py`           | Keep for HTTP/MCP rollouts                                                                                   |
| `common/safety_guard.py` | Keep; merchant agents need tool/code safety                                                                  |
| `serve/`                 | Keep; RLE rollouts will need remote workers                                                                  |

AppWorld supports in-process API use via FastAPI `TestClient`, while also supporting served APIs and Docker deployment; keep that because RL rollouts will need both cheap local execution and isolated remote execution. ([GitHub][1])

# Replace AppWorld Apps With Commerce Apps

## 1. `shopify_admin`

Core state:

```text
Shop
Product
ProductVariant
InventoryItem
InventoryLevel
Location
Order
LineItem
FulfillmentOrder
Fulfillment
Customer
Refund
Transaction
Discount
Metafield
FlowRule
CashLedgerEntry
```

Core tools:

```text
graphql_query
graphql_mutation
orders_search
order_get
order_refund_create
order_cancel
order_note_update
products_search
product_create
product_update
variant_update
inventory_levels_get
inventory_adjust
fulfillment_orders_list
fulfillment_create
fulfillment_tracking_update
customer_get
customer_tags_update
discount_create
discount_deactivate
metafield_set
flow_rule_create
```

## 2. `suppliers`

```text
supplier_catalog_search
supplier_quote_request
purchase_order_create
purchase_order_status
supplier_message_send
```

## 3. `logistics`

```text
shipment_track
shipment_reroute
claim_lost_package
carrier_rate_quote
```

## 4. `customers`

```text
customer_inbox_search
customer_message_send
complaint_resolve
return_authorize
```

## 5. `ads`

```text
campaign_create
campaign_update_budget
campaign_pause
campaign_report
```

## 6. `storefront`

```text
traffic_tick
product_page_report
cart_abandonment_report
conversion_report
```

# RLE Episode Shape

```python
@dataclass
class ShopWorldTask:
    task_id: str
    store_archetype: str
    instruction: str
    initial_state_path: str
    start_datetime: str
    episode_days: int
    allowed_tools: list[str]
    reward_spec: dict
    hidden_events_seed: int
```

Example:

```text
Task: sw_delay_003
Instruction: Supplier delay threatens 38 open orders. Preserve margin, avoid SLA breach, and protect VIP customers.
Episode length: 7 simulated days.
Allowed tools: Shopify Admin, supplier, logistics, customer inbox.
Hidden events: 2 supplier miscommunications, 1 lost package, 1 VIP complaint.
```

# Reward Vector

Do not start with a scalar reward. Start with a vector, then scalarize later for training.

| Component              |    Direction |
| ---------------------- | -----------: |
| Gross margin           |     maximize |
| Cash balance           |     maximize |
| Revenue                |     maximize |
| Refund leakage         |     minimize |
| Stockout rate          |     minimize |
| SLA breach rate        |     minimize |
| Complaint backlog      |     minimize |
| VIP churn risk         |     minimize |
| Fraud loss             |     minimize |
| Policy violations      | hard penalty |
| Privacy leakage        | hard penalty |
| Unauthorized refunds   | hard penalty |
| API cost               |     minimize |
| Price thrashing        |     minimize |
| Long-horizon coherence |     maximize |

Scalar example:

```python
reward = (
    2.0 * gross_margin_delta
    + 1.0 * cash_delta
    + 0.5 * nps_delta
    - 3.0 * sla_breaches
    - 2.0 * stockout_days
    - 5.0 * policy_violations
    - 1.0 * api_cost_units
    - 2.0 * price_thrashing_score
)
```

# Critical Design Change Versus AppWorld

AppWorld is mostly **task completion**.

ShopWorld must be **business control**.

The agent should not only satisfy instructions. It must maintain a viable operating policy over time:

```text
observe state
→ infer business risk
→ choose action
→ update store/supplier/customer/ad state
→ simulate exogenous events
→ score financial + operational + safety outcomes
→ continue
```

That is closer to Andon’s Luna experiment than a customer-support benchmark. Luna was given real money, retail authority, inventory decisions, staffing, pricing, and a profit mandate; ShopWorld should simulate that autonomy before a real Shopify merchant grants write access. ([Andon Labs][3])

# MVP Cut Line

Build this first:

| MVP item            |    Target |
| ------------------- | --------: |
| Store archetypes    |         1 |
| Products            |        50 |
| Variants            |       150 |
| Customers           |       500 |
| Orders              |     1,000 |
| Shopify-like tools  |        25 |
| External simulators |         5 |
| Short tasks         |       100 |
| Long episodes       |         5 |
| Episode length      | 7–30 days |
| Baseline agents     |         3 |
| Reward metrics      |     12–15 |
| Public leaderboard  |     later |

# Training Loop

```text
1. Generate store snapshot.
2. Generate scenario.
3. Reset ShopWorld.
4. Agent acts through tools.
5. Environment advances simulated time.
6. Customers, suppliers, logistics, ads, and competitors react.
7. Reward vector is computed.
8. Trace is stored.
9. Counterfactual variants are generated.
10. Agent scaffold/model is hill-climbed.
```

# Counterfactual Generator

```text
same demand, lower cash
same supplier, longer lead time
same complaint, VIP customer
same orders, higher fraud
same inventory, ad spike
same product, worse reviews
same logistics, lost package
same promotion, margin compression
same campaign, creative fatigue
```

This is the main commercial training asset. The moat is not the AppWorld fork. The moat is the synthetic commerce simulator plus merchant-specific replay.

# Commercialization Implication

For a **% of profit/revenue lease model**, the benchmark should produce a merchant-facing report before deployment:

```text
Store clone readiness score
Expected profit uplift
Worst-case drawdown
Policy violation rate
Refund leakage risk
Inventory risk
Human escalation rate
Recommended write-access scope
```

Do **not** start by selling an unconstrained AI store manager. Start with staged authority:

```text
Stage 1: read-only diagnosis
Stage 2: draft actions for approval
Stage 3: bounded automations
Stage 4: capped write access
Stage 5: profit-share autonomous manager
```

# Final Architecture

```text
ShopWorld
= AppWorld runtime kernel
+ Shopify-like Admin GraphQL simulator
+ supplier/customer/logistics/ad/storefront actors
+ long-horizon business simulator
+ vector reward evaluator
+ scenario/counterfactual generator
+ rollout infrastructure
+ merchant-specific store clone import
```

# Immediate Build Order

1. Create clean `shopworld` repo from AppWorld skeleton, not from AppWorld bundled app content.
2. Preserve only runtime, task, evaluator, API docs, common utilities, serve, and minimal experiments.
3. Implement `shopify_admin` as the first app.
4. Add SQLite state models for products, inventory, orders, customers, fulfillments, discounts, and cash ledger.
5. Implement 25 Shopify-like tools.
6. Build 20 deterministic short tasks.
7. Build one 30-day Luna-style operating episode.
8. Add supplier, logistics, customer, ad, and storefront simulators.
9. Add reward vector and hard safety invariants.
10. Run baseline agents and generate the first merchant-readiness report.

[1]: https://github.com/StonyBrookNLP/appworld "GitHub - StonyBrookNLP/appworld:  AppWorld: A Controllable World of Apps and People for Benchmarking Function Calling and Interactive Coding Agent, ACL'24 Best Resource Paper. · GitHub"
[2]: https://github.com/StonyBrookNLP/appworld/blob/main/guides/developing_new_apps.md "appworld/guides/developing_new_apps.md at main · StonyBrookNLP/appworld · GitHub"
[3]: https://andonlabs.com/blog/andon-market-launch?utm_source=chatgpt.com "We gave an AI a 3 year retail lease in SF and asked it to ..."
