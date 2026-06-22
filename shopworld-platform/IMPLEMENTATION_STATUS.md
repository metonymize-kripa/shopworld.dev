# ShopWorld Implementation Status

## Summary

Core implementation of the ShopWorld platform is complete, providing the foundational infrastructure for a deterministic RL environment simulating Shopify merchant operations.


## 2026-06-22 Update: Merchant API Surface Vertical Slice

Implemented a first concrete agent-visible Merchant API Surface in `shopworld.api_surface` and kept it separate from hidden simulator/evaluator state. The surface now exposes the initial contract from `platform-rnd/README.md` for orders, customers, fulfillments, inventory, refunds, products, discounts, tickets, and policy lookup/explanation.

### Decisions Captured

1. **API surface is a Python tool facade first** - The first implementation is a deterministic in-process facade over the canonical SQLModel database so benchmark runners and tests can exercise tool semantics before adding MCP/HTTP transports.
2. **No hidden state leakage** - Tool serializers only return merchant-visible fields; scenario hidden state, evaluator labels, expected actions, rewards, and future events remain outside the facade.
3. **Policy checks live at mutation boundaries** - Cancellation and fulfillment cancellation now reject already-fulfilled/successful states at the tool boundary, matching the active contract that agents must operate through guarded merchant tools.
4. **Stable normalized tool result** - Every tool returns a `ToolResult` with `ok`, `data`, and `errors` so LLM agents, milli.run adapters, and the neutral benchmark runner can share one response shape.

### Newly Completed

- `shopworld.api_surface.MerchantAPISurface` with 21 named tools covering the initial Merchant API Surface contract.
- `ShopWorldEnv.step()` can execute dotted Merchant API tool names through the same facade while preserving legacy action names.
- Unit coverage proving the registry includes the contract tools, ticket replies do not leak hidden tracking state, order lookup works through the facade, fulfilled orders cannot be cancelled through the exposed tool, and environment steps execute dotted ticket tools.

### Still Remaining

- Promote the current coarse dotted-tool scope mapping into a documented per-tool authorization table with tests for each write/read scope.
- Add returns and shipment-specific tool families once the supporting models are promoted from post-MVP stubs.
- Add MCP/HTTP transports on top of the same facade instead of creating a second API implementation.

## Completed Components

### Phase 1: Project Structure
- `pyproject.toml` - Package configuration with SQLModel, FastAPI, Strawberry GraphQL
- `README.md` - Project overview and quick start
- Directory structure following clean-room architecture

### Phase 2: Core Runtime (environment.py)
- `ShopWorldEnv` class with Gym-like interface:
  - `reset(seed)` - Initialize episode state
  - `step(action)` - Execute agent action, advance world
  - `save_state()` / `load_state()` - Snapshot/restore for training
  - `evaluate()` - Generate evaluation results
- Multi-dimensional reward vector computation
- Trace recording for analysis and replay
- Simulated clock with business hours awareness
- Scope/permission checking
- Policy violation detection
- Query cost budget tracking

### Phase 3: Task System (task.py)
- `Task` dataclass for scenario definitions:
  - Initial state specification (DB records + hidden state)
  - Success/failure condition definitions
  - Allowed scopes and authority levels
  - Difficulty grading (1-3)
- `TaskLoader` for task library management
- `TaskGenerator` for counterfactual variants
- Templates for common task types (support, inventory, fulfillment)

### Phase 4: Evaluation Engine (evaluator.py)
- `EvaluationResult` with comprehensive metrics:
  - Task completion scoring
  - Collateral damage detection
  - Policy violation counts by type
  - Business impact (revenue, margin, cash)
  - Operational metrics (SLA, backlog, response time)
  - API efficiency scores
  - Coherence checks (price thrashing detection)
- `to_readiness_report()` for merchant-facing output
- Staged authority recommendation (read-only → autonomous)

### Phase 5: Backend Database Layer (`backend/db.py`)
- `Database` SQLite manager with SQLModel
- Session context manager
- Deterministic in-memory SQLite setup via `StaticPool`
- `init_database()` factory function
- Legacy `apps/lib/db.py` compatibility shim for existing imports

### Phase 6: Commerce Models (apps/shopify_admin/models.py)
Complete Shopify-like schema:

**Catalog:**
- `Product` - Core product entity
- `ProductVariant` - Size/color variants
- `Collection` / `CollectionProductLink` - Grouping
- `Metafield` - Custom data

**Inventory:**
- `InventoryItem` - SKU tracking
- `Location` - Warehouse/store
- `InventoryLevel` - Quantity by location

**Customers:**
- `Customer` - Full customer profile
- Order history, total spent, tags

**Orders:**
- `Order` - Purchase lifecycle
- `OrderLineItem` - Line items
- `FulfillmentOrder` - Fulfillment grouping
- `Fulfillment` - Shipment records
- `FulfillmentLineItem` - Shipped items
- `Refund` / `RefundLineItem` - Refunds

**Discounts:**
- `DiscountCode` - Percentage/fixed discounts

**Support (ShopWorld-specific):**
- `SupportTicket` - Customer complaints
- `SupportMessage` - Ticket messages
- Sentiment tracking, SLA deadlines

### Phase 7: GraphQL API (apps/shopify_admin/graphql.py)
- Strawberry GraphQL schema
- **Queries:**
  - `shop` - Shop information
  - `product` / `products` - Product lookup
  - `order` / `orders` - Order lookup
  - `customer` / `customers` - Customer lookup
  - `inventory_levels` - Stock levels
  - `support_tickets` - ShopWorld-specific
- **Mutations:**
  - `product_update` - Edit products
  - `inventory_adjust_quantities` - Stock adjustments
  - `refund_create` - Issue refunds

### Phase 8: Utilities (common/)
- `SimulatedClock` - Deterministic time advancement
- `StateSnapshot` - Serialization for reset/restore
- `state_diff()` - Detect unauthorized changes
- Exception hierarchy for errors

### Phase 9: Examples and Tests
- `hello_world.py` - Minimal usage example
- `test_environment.py` - Environment tests
- `test_models.py` - Database model tests

## Project Structure

```
shopworld-platform/
├── pyproject.toml
├── README.md
├── IMPLEMENTATION_STATUS.md
├── src/shopworld/
│   ├── __init__.py
│   ├── environment.py      # Core RLE
│   ├── task.py              # Task definitions
│   ├── evaluator.py         # Evaluation engine
│   ├── reward.py            # Reward vector
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── README.md       # Backend library boundaries and migration plan
│   │   └── db.py           # Canonical SQLModel database helpers
│   ├── common/
│   │   ├── __init__.py
│   │   ├── datetime.py      # SimulatedClock
│   │   ├── errors.py        # Exceptions
│   │   └── serialization.py # State snapshots
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── lib/
│   │   │   ├── __init__.py
│   │   │   └── db.py        # Compatibility shim to backend.db
│   │   └── shopify_admin/
│   │       ├── __init__.py
│   │       ├── models.py    # Commerce entities
│   │       └── graphql.py   # GraphQL API
│   └── examples/
│       ├── __init__.py
│       └── hello_world.py
├── tests/
│   ├── __init__.py
│   ├── test_environment.py
│   └── test_models.py
├── generate/               # (empty - for future)
├── experiments/            # (empty - for future)
└── reports/                # (empty - for future)
```

## Remaining Work

### High Priority
1. **Backend Library Modularization** - Extract persistence, runtime, commerce, policy, simulation, and evaluation libraries behind canonical `shopworld.backend.*` imports
2. **Actor Simulators** - Customer, supplier, logistics, demand, ad simulators
3. **Tool Implementations** - Complete 25+ Shopify-like tools
4. **Initial Task Library** - 20+ scenarios with real test data
5. **Integration Tests** - End-to-end episode tests

### Medium Priority
5. **MCP Server** - Model Context Protocol serving
6. **HTTP API** - REST endpoint for remote agents
7. **Support Inbox Logic** - Sentiment, SLA, customer response generation
8. **Policy Supervisor** - Merchant policy enforcement
9. **Curriculum Generator** - Difficulty-graded task sequences
10. **Counterfactual Generator** - Variant task creation

### Lower Priority
11. **Readiness Report Generator** - Formatted merchant reports
12. **Baseline Agents** - ReAct, function-calling examples
13. **Store Import Pipeline** - Read-only Shopify data import
14. **Gym Wrapper** - OpenAI Gymnasium compatibility
15. **Leaderboard** - Public benchmark infrastructure

## Next Steps

To continue implementation:

1. **Install dependencies:**
   ```bash
   cd shopworld-platform
   pip install -e ".[dev]"
   ```

2. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

3. **Try example:**
   ```bash
   python -m shopworld.examples.hello_world
   ```

4. **Continue backend modularization** using `src/shopworld/backend/README.md` as the extraction plan

5. **Implement actor simulators** (customers, suppliers, logistics)

6. **Create initial task scenarios** with real database seed data

7. **Build out tool implementations** connecting GraphQL to database mutations

## Architecture Decisions Made

1. **Simulated Shopify First** - Clean-room implementation, not depending on AppWorld bundles
2. **SQLModel/SQLite** - Fast, deterministic, easy snapshot/restore
3. **Strawberry GraphQL** - Python-native, type-safe, realistic Shopify-like API
4. **Vector Rewards** - Multi-dimensional before scalar (better for product reporting)
5. **Merchant Readiness Focus** - Evaluation → Reports → Staged deployment path
6. **Deterministic Episodes** - Full replay capability for training and debugging
