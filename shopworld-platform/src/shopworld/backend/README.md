# ShopWorld backend library modularization

`shopworld.backend` is the landing zone for backend libraries that are shared by
multiple simulators, GraphQL surfaces, task loaders, and evaluation runtimes.
The goal is to keep domain-specific app modules small while giving common
platform concerns a stable import path.

## Current modules

| Module | Responsibility | Notes |
|---|---|---|
| `shopworld.backend.db` | SQLModel engine/session setup and deterministic SQLite initialization. | Canonical replacement for the legacy `shopworld.apps.lib.db` path. |

## Target library boundaries

The platform should grow by extracting cohesive backend libraries rather than by
adding more cross-cutting code to `environment.py` or individual app packages.
Use these boundaries when moving existing code or adding new vertical slices:

| Library | Owns | Should not own |
|---|---|---|
| `shopworld.backend.persistence` | Database/session lifecycle, snapshot storage, fixture loading. | Shopify-specific models or task scoring. |
| `shopworld.backend.runtime` | Episode lifecycle, clocks, traces, action dispatch, deterministic event loop. | Domain business rules. |
| `shopworld.backend.commerce` | Shared commerce concepts: money, IDs, inventory quantities, order lifecycle enums. | GraphQL resolver wiring. |
| `shopworld.backend.policy` | Scope checks, authority levels, merchant constraints, policy violation records. | Reward weighting or presentation. |
| `shopworld.backend.simulation` | Actor simulator contracts, seeded randomness, scheduled event interfaces. | Concrete customer/supplier/logistics domain data. |
| `shopworld.backend.evaluation` | Metric primitives, collateral-damage checks, readiness report data contracts. | Frontend rendering. |

## Migration plan

1. **Stabilize canonical imports.** New shared infrastructure should import from
   `shopworld.backend.*`; compatibility shims may remain under older app paths
   until downstream code is migrated.
2. **Extract contracts before implementations.** Define protocols/data contracts
   for simulators, action dispatch, policy checks, and evaluators before moving
   larger modules.
3. **Move one vertical slice at a time.** Start with support/WISMO because it
   exercises customers, orders, fulfillment, refunds, scopes, and collateral
   damage in one deterministic workflow.
4. **Keep app packages domain-focused.** `shopworld.apps.shopify_admin` should
   expose Shopify-like models and GraphQL behavior, while reusable mechanics
   move to backend libraries.
5. **Retire shims deliberately.** Each compatibility shim should name its
   canonical replacement and be removed only after tests and examples use the
   new path.

## Acceptance criteria for future extractions

- Existing tests continue to pass without fixture rewrites.
- Public examples use canonical `shopworld.backend.*` imports for shared
  services.
- A moved module has a clear owner and no circular dependency on an app package.
- Documentation names whether an API is canonical, compatibility-only, or
  experimental.
