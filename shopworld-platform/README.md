# ShopWorld

A deterministic reinforcement learning and evaluation environment for AI agents that operate Shopify merchant businesses.

## Overview

ShopWorld lets merchants stress-test AI store managers in a private simulated clone before granting live store access. It answers:

1. What workflows can this agent perform safely?
2. What permission scopes should the merchant grant?
3. What is the expected uplift and downside risk before deployment?

## Core Features

- **Simulated Shopify World**: Deterministic commerce environment with customers, suppliers, logistics, and advertising
- **Shopify Admin GraphQL Simulator**: Realistic API surface with scopes, pagination, and throttling
- **Support Inbox**: Stateful customer service interactions with sentiment and policy compliance
- **Actor Simulators**: Synthetic customers, shoppers, suppliers, carriers, and ad venues
- **Vector Reward Evaluation**: Business, customer, operational, API, and safety metrics
- **Merchant-Specific Twins**: Import store data for private, realistic evaluation
- **Readiness Reports**: Workflow-by-workflow safety assessments and staged deployment recommendations

## Quick Start

### Using `uv` (recommended)

```bash
# Run with uv (no install needed)
uv run shopworld hello

# Run tests
uv run pytest tests/

# Run example
uv run python -m shopworld.examples.hello_world

# Install for development
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Install
pip install -e ".[dev]"

# Run CLI
shopworld hello

# Run tests
pytest tests/
```

## Architecture

```
shopworld/
  environment.py      # Core RLE: reset, step, state management
  task.py            # Scenario definitions and loading
  evaluator.py       # State-based and trace-based grading
  reward.py          # Multi-dimensional reward vector
  apps/
    shopify_admin/   # Simulated Shopify GraphQL API
    suppliers/       # Supplier simulator
    logistics/       # Carrier/fulfillment simulator
    customers/       # Customer/shopper simulator
    ads/             # Advertising venue simulator
```

## Development

See [Product Research and Implementation Plan](../platform-rnd/shopworld-product-research-implementation-plan.md) for detailed specifications.

## License

Apache-2.0
