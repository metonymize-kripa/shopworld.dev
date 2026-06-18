# ShopWorld Repository Code Review: Critical Analysis and Streamlining Plan

_Date: 2026-06-18_

## Executive summary

The repository currently contains two related but operationally different products:

1. **`shopworld.dev` / Drop Day** — a compact Vite + React marketing/game application with a Vercel signup function.
2. **`shopworld-platform`** — a Python package intended to become a deterministic Shopify-like reinforcement-learning and evaluation environment.

Both directions are promising, but the codebase is still in a prototype/research phase. The highest-leverage improvement is to make the repository intentionally monorepo-shaped: document which package owns which outcome, add repeatable quality gates for both runtimes, and harden the core simulator loop before expanding feature surface area. The React app is relatively small and shippable, while the Python platform has stronger product ambition but many placeholder seams, duplicated GraphQL APIs, and insufficient integration between models, database state, environment stepping, simulators, and evaluation.

## Review scope and method

This review covered the repository root, the Vite/React app, the Vercel API function, the `platform-rnd` planning documents, and the Python `shopworld-platform` package. It included static inspection of source files and attempted build/test execution.

Commands run during review:

```bash
rg --files -g '!node_modules'
npm run build
cd shopworld-platform && uv run pytest tests/
```

## Repository map

| Area | Current role | Observations |
| --- | --- | --- |
| Root Vite app | Public-facing game / landing experience | Small and easy to reason about; game logic and state are mostly concentrated in `src/App.jsx` and `src/gameData.js`. |
| `api/signup.js` | Vercel serverless email capture | Simple and pragmatic, but has concurrency, abuse-control, and data-governance risks before public use. |
| `platform-rnd/` | Product, API, and research planning | Valuable context, but decisions are spread across many documents and need a current architecture decision record/index. |
| `shopworld-platform/` | Python RL/evaluation simulator package | Strong conceptual structure, but core loop has placeholders, duplicated GraphQL layers, incomplete database wiring, and tests that mostly validate scaffolding. |

## What is working well

### 1. Clear product thesis

The platform README articulates a strong and differentiated goal: evaluate AI store managers in a private simulated commerce environment before giving them live store permissions. That framing gives the repository a useful north star: safety, measurable outcomes, scoped authority, and realistic Shopify API behavior.

### 2. Small root app with a focused user loop

The Drop Day app has a simple loop, clear constants, and centralized game data. This is good for iteration speed and lowers onboarding cost for contributors. Product/catalog tuning lives mostly in `src/gameData.js`, while runtime screens and transitions are in `src/App.jsx`.

### 3. Platform package has the right conceptual modules

The Python package already separates environment stepping, task definitions, reward vectors, evaluation, Shopify Admin models, actor simulators, and store generation. That is the right set of seams for a simulator/evaluation product.

### 4. GraphQL realism is explicitly valued

The expanded GraphQL API work acknowledges important Shopify-specific behaviors: GIDs, connections, query cost, throttling, scopes, and `userErrors`. This is exactly the fidelity needed if agents are expected to transfer habits from simulation to production.

## Critical issues and recommended improvements

## A. Repository structure and product boundaries

### Issue A1 — The repository presents two products without a unifying workspace contract

The root README describes a Vite game and serverless signup flow, while `shopworld-platform/README.md` describes a Python RL platform. Both are valid, but the repository does not currently explain whether the game is a demo/marketing artifact, an example environment, or a separate product.

**Impact:** contributors cannot easily tell which commands are canonical, what CI should run, or how changes in one package affect the other.

**Recommendation:** add a root-level monorepo guide that declares:

- package ownership and purpose;
- canonical commands for app build, Python tests, formatting, and linting;
- release/deployment targets;
- the relationship between Drop Day and the ShopWorld platform;
- whether `platform-rnd/` documents are historical, canonical, or superseded.

### Issue A2 — `node_modules/` is currently untracked but present in the working tree

`git status --short` showed `?? node_modules/`. This suggests local dependency artifacts are not being ignored or cleanup discipline is inconsistent.

**Impact:** accidental commits become likely, command output gets noisy, and reviewers may miss meaningful changes.

**Recommendation:** ensure root `.gitignore` covers `node_modules/`, `dist/`, platform virtualenvs, caches, and OS files. Keep generated artifacts out of commits unless intentionally vendored.

## B. Root React/Vercel app

### Issue B1 — Game state machine is concentrated in one large component

`src/App.jsx` owns the screen router, game lifecycle, timers, local mutable refs, restock flow, end screens, and signup UI. This works for a prototype but will become brittle as features are added.

**Impact:** future changes to balance, analytics, accessibility, persistence, or tutorials will increase regression risk.

**Recommendation:** extract:

- a `useGameSession` hook for day/customer timers and transitions;
- pure game reducers for state transitions;
- screen components into separate files;
- business logic tests for timeout, stock depletion, day-end, and restock behavior.

### Issue B2 — Timer state mixes React state and mutable refs

The Play screen uses `localRef` to keep cash, reputation, stock, profit, and served values synchronized with intervals. This avoids stale closures but creates a second source of truth alongside React state.

**Impact:** bugs can occur when a screen unmounts, intervals race with `setGame`, or future persistence/analytics reads stale state.

**Recommendation:** move game state to a reducer and dispatch events (`CUSTOMER_LEFT`, `PRODUCT_PICKED`, `DAY_ENDED`). Timers should dispatch events rather than mutate a side ref.

### Issue B3 — Signup endpoint is functional but not production-hardened

`api/signup.js` validates a basic email regex, reads a single JSON blob, appends if absent, and overwrites the blob. It intentionally no-ops when Blob storage is not configured.

**Risks:**

- concurrent writes can lose signups because read/modify/write is not atomic;
- no rate limiting or bot protection;
- no request-size guard;
- returned `detail` on storage failure may leak implementation information;
- no explicit consent/privacy fields.

**Recommendation:** before public launch, either move to a storage primitive with atomic inserts or add optimistic concurrency/retry semantics. Add rate limiting, honeypot/CAPTCHA strategy, request-size limits, structured logging, and privacy/consent metadata.

### Issue B4 — No frontend test or lint safety net

The root package has only `dev`, `build`, and `preview` scripts.

**Impact:** scoring changes, UI state transitions, and signup validation can regress silently.

**Recommendation:** add Vitest for `resolveOrder`, day goals/restock math, and signup client behavior; add ESLint/Prettier or Biome; add a single `npm run check` command.

## C. Python platform architecture

### Issue C1 — Core environment loop is still mostly scaffolded

`ShopWorldEnv` has the right public API (`reset`, `step`, `evaluate`), but many methods are placeholders: database initialization references a non-existent module, simulators are not actually instantiated, current state serialization returns `{}`, observations are empty, support/fulfillment/inventory event processing is `pass`, and business metrics are fixed zeros.

**Impact:** current tests can pass shape checks while the platform does not yet simulate meaningful commerce state transitions. This is the biggest gap between the README promise and implementation reality.

**Recommendation:** prioritize a thin vertical slice before broad API expansion:

1. initialize an in-memory SQLModel database;
2. load generated store records;
3. expose visible products/orders/customers/inventory in observations;
4. execute one or two real actions against the database;
5. run one simulator that creates observable events;
6. evaluate a concrete task end-to-end.

### Issue C2 — Determinism is not fully isolated

`reset(seed=...)` seeds Python's global random module, and task generation also seeds global random. Actor simulators use local `random.Random`, which is better.

**Impact:** deterministic claims can break when unrelated code consumes global randomness.

**Recommendation:** pass an episode RNG object through task generation, store generation, and simulators. Avoid mutating global random state except in tests that explicitly need it.

### Issue C3 — The database boundary is unclear

The environment intends to initialize a SQLModel database, but `_init_database` imports `shopworld.apps.lib.db`, which does not appear in the repository. `_load_task_records` is a placeholder, and `_get_current_state` returns an empty dict.

**Impact:** environment stepping, evaluation, collateral-damage detection, and task completion all operate without real state.

**Recommendation:** create a concrete `shopworld.common.db` or `shopworld.storage` module with:

- engine/session creation;
- schema creation;
- deterministic seed loading from `StoreSeeder` and `Task.initial_db_records`;
- snapshot serialization for all core tables;
- transaction boundaries around each step.

### Issue C4 — Two GraphQL implementations compete

There is an older `shopworld.apps.shopify_admin.graphql.py` and a newer expanded `graphql_api/` package with separate schema, cost, pagination, scopes, queries, and mutations.

**Impact:** duplication creates unclear ownership and makes it harder to know which API agents should use. Tests may validate one layer while product work happens in the other.

**Recommendation:** designate `graphql_api.schema.build_schema()` as the canonical implementation, migrate missing behavior from `graphql.py`, then deprecate or delete the older module. Keep a compatibility shim only if needed.

### Issue C5 — Scope enforcement exists in multiple layers but is not unified

The environment has `_get_required_scope()` for simple tool names, while `graphql_api/scopes.py` defines operation-level Shopify-like scope requirements.

**Impact:** agents may receive different authorization behavior depending on whether they use environment tools or GraphQL operations.

**Recommendation:** make GraphQL scope requirements the source of truth. Environment tools should map to operations or use the same policy registry. Add tests for denied queries, denied mutations, and allowed bundle behavior.

### Issue C6 — Evaluation currently risks scoring empty or synthetic data

`Evaluator` is much more detailed than `ShopWorldEnv.evaluate()`, but the environment's own evaluation path returns placeholder business metrics and state diffs over `{}`. The richer evaluator is not clearly wired into the environment lifecycle.

**Impact:** readiness reports may look authoritative without being grounded in real state transitions.

**Recommendation:** make `Evaluator.evaluate()` the canonical path. Require it to consume initial snapshots, final snapshots, and trace steps from the environment. Add fixtures where an unsafe action visibly changes an unauthorized table and is caught.

### Issue C7 — Task library loading is incomplete

`TaskLoader.load_all()` exists, but CLI `run` creates a loader and immediately calls `get_task()` without loading tasks. The `tasks/` package contains Python task scaffolding rather than JSON scenarios expected by the loader.

**Impact:** the CLI run path likely cannot find tasks, and there is no canonical scenario format.

**Recommendation:** choose one scenario format for MVP. If JSON is preferred, add sample JSON tasks and call `load_all()` in the CLI. If Python-defined tasks are preferred, update `TaskLoader` accordingly.

### Issue C8 — Simulator modules are promising but disconnected

Customer, logistics, and supplier simulators each maintain internal state and produce events, but environment initialization currently sets them to `None`.

**Impact:** core features promised by the README — synthetic customers, suppliers, carriers, support inbox — are not actually exercised by episodes.

**Recommendation:** start with one deterministic simulator path, such as WISMO support tickets:

- seed store with orders and fulfillments;
- create package state in `LogisticsSimulator`;
- emit a late-shipment event;
- create a support ticket;
- let an agent query order/tracking and reply;
- evaluate resolution quality and SLA.

## D. Testing and quality gates

### Issue D1 — Python test run is currently blocked by dependency download failure

Attempting `cd shopworld-platform && uv run pytest tests/` created a virtualenv but failed to download `idna==3.18` because of a tunnel/network error. This is an environment limitation from the attempted run, but it also shows the test path depends on resolving dependencies at runtime.

**Recommendation:** document the expected Python version and add CI caching/lockfile usage. For local offline resilience, consider checking whether the committed `uv.lock` matches `pyproject.toml` and documenting `uv sync --frozen`.

### Issue D2 — Tests are mostly structural rather than behavioral

Existing environment tests assert initialization, reset shape, step increments, trace presence, and simple task scope application. These are useful smoke tests, but they do not prove commerce state mutation, GraphQL resolver behavior, policy safety, or evaluator correctness.

**Recommendation:** add tests for:

- deterministic store seeding with same seed;
- database snapshot diffing;
- GraphQL pagination and scope denial;
- mutation `userErrors` for invalid inputs;
- query-cost budget exhaustion;
- one complete task from reset to successful evaluation;
- failed task with collateral damage.

### Issue D3 — Lint/type tools are configured but not integrated

`pyproject.toml` configures Black, Ruff, and mypy, but there is no top-level command that runs all checks across the monorepo.

**Recommendation:** add a root `Makefile`, `justfile`, or package script equivalent:

```bash
make check        # npm build/test + uv run pytest + ruff + mypy
make format       # frontend formatter + black/ruff format
make app-dev
make platform-test
```

## E. Documentation and research hygiene

### Issue E1 — `platform-rnd/` needs an index and decision status

The research folder contains many useful documents, but their status is not explicit. Some appear to be plans from different model runs or alternative designs.

**Impact:** new contributors may not know which plan is canonical.

**Recommendation:** add `platform-rnd/README.md` with:

- current active spec;
- superseded docs;
- open questions;
- architecture decisions made;
- next review date.

### Issue E2 — Implementation status should be generated or regularly reconciled

`shopworld-platform/IMPLEMENTATION_STATUS.md` is useful, but status documents easily drift from code. The GraphQL API README also has a status table that may conflict with the expanded implementation.

**Recommendation:** convert status into an ADR/checklist with owners and dates, and add tests that back claims like “pagination implemented” or “scope enforcement implemented.”

## F. Security, privacy, and safety

### Issue F1 — Signup storage should be treated as PII

Email capture is intentionally minimal, but emails are personal data.

**Recommendation:** add privacy text in UI, avoid returning implementation details from errors, log only anonymized metadata, and document data retention/deletion procedures.

### Issue F2 — Agent safety model needs executable guardrails

The platform thesis depends on permissioning, policy constraints, and collateral-damage detection. These concepts exist in code names, but not yet as end-to-end enforced invariants.

**Recommendation:** implement tests that intentionally attempt unsafe actions and assert:

- action is blocked;
- violation is recorded in trace;
- reward penalizes it;
- final readiness report recommends against deployment.

## Prioritized roadmap

### P0 — Make the repo reliable to work in

- Add root `.gitignore` coverage for generated artifacts.
- Add root developer guide with canonical commands.
- Add CI or a `make check` command for app build and platform tests/lint.
- Add `platform-rnd/README.md` to identify canonical docs.

### P1 — Build one real simulator vertical slice

- Implement database/session initialization.
- Load deterministic store records.
- Instantiate one simulator.
- Create observable support/inventory/logistics events.
- Execute real actions against state.
- Evaluate a single task with real pass/fail checks.

### P2 — Consolidate API and policy layers

- Make `graphql_api/` canonical.
- Deprecate duplicate `graphql.py`.
- Use one scope registry across tools and GraphQL.
- Add GraphQL behavior tests for pagination, scopes, throttling, and `userErrors`.

### P3 — Harden the public app

- Extract game reducer/hooks.
- Add tests for scoring and day transitions.
- Harden signup endpoint for concurrency and abuse.
- Add analytics only after privacy posture is clear.

### P4 — Improve evaluation credibility

- Wire `Evaluator` into environment output.
- Define readiness report thresholds.
- Add collateral-damage fixtures.
- Add reproducibility tests across seeds and snapshots.

## Suggested streamlined target architecture

```text
shopworld.dev/
  README.md                 # monorepo purpose + commands
  package.json              # app scripts
  api/                      # Vercel functions
  src/                      # Drop Day app
  platform-rnd/             # research, ADRs, canonical plans
  shopworld-platform/
    pyproject.toml
    src/shopworld/
      environment.py        # Gym-like episode API
      storage/              # SQLModel engine, fixtures, snapshots
      apps/shopify_admin/
        graphql_api/        # single canonical GraphQL API
        models.py
      simulators/ or apps/  # customer/supplier/logistics actors
      evaluation/           # evaluator + reports
      tasks/                # canonical scenario definitions
    tests/
      unit/
      integration/
      fixtures/
```

## Closing assessment

The repository has a compelling product thesis and enough scaffolding to show the intended shape. The main risk is continuing to expand breadth — more GraphQL fields, more planning docs, more simulators — before one complete deterministic evaluation loop is real. Streamlining should therefore focus less on adding surface area and more on making one path production-quality: seed state, expose realistic API, perform agent action, mutate world, simulate consequences, evaluate safety/business impact, and reproduce the result.
