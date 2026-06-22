# Component simulator architecture

ShopWorld should present component-level simulators as reusable slices of the same platform thesis, not as unrelated demos. The directory layout now separates scenario facts, React presentation, and the Python evaluation runtime so each part can mature independently.

## Canonical structure

```text
packages/shopworld-scenarios/
  src/runtime.js          Shared ShopWorld boundary and tool-family taxonomy
  src/support/index.js    Post-purchase support scenario fixtures
  src/wismo/index.js      WISMO/order-exception scenario fixtures
support-sim/              React presentation for support workflow choices
wismo-sim/                React presentation for WISMO/API/state-transition choices
shopworld-platform/       Deterministic simulator, merchant API surface, evaluator, traces
platform-rnd/README.md    Active product plan and boundary contract
```

## Dependency direction

```text
platform-rnd/README.md
        │
        ▼
packages/shopworld-scenarios  ─────► support-sim
        │                         └► wismo-sim
        ▼
shopworld-platform tasks, fixtures, and evaluator tests
```

The scenario package is UI-free on purpose. Demo apps can render it today; platform tasks can ingest the same scenario concepts later without copying UI code.

## Boundary rules

1. React simulators may show workflow steps, API-call names, state-transition labels, and sales narrative.
2. React simulators must not own hidden simulator truth, reward functions, or evaluator logic.
3. `shopworld-platform/` owns deterministic state transitions, merchant API contracts, traces, scoring, and readiness reports.
4. New component sims should start as fixture modules under `packages/shopworld-scenarios/src/<domain>/` plus a thin rendering layer.
5. Any scenario that becomes important enough for a customer demo should have a path to a platform task and evaluator check.

## Why this supports the milli.run pitch

The demos should help clients feel the cost of leaving granular runtime choices to an unconstrained AI: when to query, when to mutate, when to escalate, what policy applies, which authority scope is safe, and which hidden consequence matters. The platform then turns that intuition into repeatable evaluation evidence for milli.run.
