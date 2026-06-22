# ShopWorld Platform

ShopWorld Platform is the deterministic runtime for evaluating AI agents that operate Shopify-like merchant workflows. It is the backend counterpart to the root `shopworld.dev` demo: the web app explains the thesis, while this package provides seeded tasks, simulated APIs, rewards, traces, and readiness reporting.

## What the platform evaluates

ShopWorld focuses on agentic commerce rather than generic office automation. A candidate agent is expected to reason across:

- Shopify-like Admin GraphQL queries and mutations.
- Customer support state, especially post-purchase/WISMO workflows.
- Inventory, fulfillment, supplier, logistics, and customer simulators.
- Policy scopes and authority levels.
- Business, customer, operational, API-efficiency, and safety metrics.

The product goal is not just “task success.” Evaluations should also detect collateral damage: incorrect refunds, unsafe inventory edits, unnecessary discounts, missed escalations, privacy violations, overpromises, and other state changes a merchant would care about before granting write access.

## Current package shape

```text
src/shopworld/
  environment.py      Gym-like deterministic episode runtime
  task.py             Scenario definitions, loaders, and variants
  evaluator.py        State/trace grading and readiness-report primitives
  reward.py           Multi-dimensional reward vector
  apps/
    shopify_admin/    Shopify-like models and GraphQL wrapper
    customers/        Customer/support simulator
    logistics/        Fulfillment/logistics simulator
    suppliers/        Supplier simulator
  common/             Clock, errors, serialization helpers
  generate/           Seed-store generation helpers
  examples/           Minimal usage examples
```

The canonical Shopify-like GraphQL work is moving toward `src/shopworld/apps/shopify_admin/graphql_api/`. Keep overlapping API surfaces aligned until older wrappers are fully migrated and tested.

## Quick start

From this directory:

```bash
uv sync --frozen --all-extras
uv run shopworld hello
uv run python -m shopworld.examples.hello_world
uv run pytest tests/
```

From the repository root, prefer the Makefile targets:

```bash
make platform-test
make platform-lint
make platform-type
make platform-check
```

## Development guardrails

- Build complete deterministic vertical slices before adding broad API breadth.
- Keep task fixtures, world transitions, and evaluator assertions in sync.
- Treat support/WISMO as the first priority slice because it exercises customers, orders, fulfillment, refunds, policy, and collateral damage together.
- Add tests for every behavior the readiness report claims to measure.
- Use `platform-rnd/README.md` to distinguish active planning references from historical notes.

## License

Apache-2.0
