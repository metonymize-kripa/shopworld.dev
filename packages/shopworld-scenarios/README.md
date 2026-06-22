# @shopworld/scenarios

Shared scenario fixtures and runtime taxonomy for ShopWorld demos and future platform tests.

This package is intentionally UI-free. React apps import these fixtures to render component-level simulators, while `shopworld-platform/` can later load the same scenario shape to build deterministic tasks, tool contracts, and evaluator checks.

## Modules

- `./support` — post-purchase support workflow scenarios and verdict metadata.
- `./wismo` — WISMO/order-exception scenarios, workflow levels, API calls, and state-transition fixtures.
- `./runtime` — boundary and tool-family taxonomy aligned with `platform-rnd/README.md`.

## Rules

- Agent-visible fields belong in scenario/tool fixtures.
- Hidden evaluator truth belongs in platform tasks, not demo components.
- Demo apps should compose scenario data; they should not own product planning or simulator policy.
