# shopworld.dev — Agentic Commerce Simulator

shopworld.dev is a focused simulator for evaluating AI agents that operate commerce workflows. The repository now has one coherent product view: a public, lightweight web demo at the root and a Python evaluation platform in `shopworld-platform/`. Both point at the same thesis: before a merchant gives an agent write access, the agent should prove it can make profitable, policy-safe commerce decisions in a deterministic sandbox.

## Product thesis

ShopWorld is an AppWorld-style simulator narrowed to agentic commerce. It models the messy operating surface of a Shopify-like merchant business: ambiguous customer intent, inventory pressure, refunds, fulfillment exceptions, policy boundaries, API scopes, and delayed consequences.

The MVP should answer three questions:

1. Can the agent complete the requested commerce workflow?
2. Did it avoid collateral damage such as wrong refunds, inventory corruption, unsafe discounts, or customer overpromises?
3. What authority level is safe for the agent: read-only, draft-only, supervised operator, or autonomous operator?

## Repository map

| Area | Role | Status |
| --- | --- | --- |
| Root Vite app (`src/`, `api/`, `public/`) | Public-facing interactive demo for the ShopWorld thesis. It compresses agentic commerce decisions into a short “Agent Sprint” game loop. | Canonical web app. |
| `support-sim/` | Deployable post-purchase support scenario explorer. It illustrates which agentic-commerce workflows are native, app-assisted, manual, or chaotic. | Scenario explorer; kept deployable for existing Vercel projects. |
| `wismo-sim/` | Deployable WISMO/order-exception deep dive with API, data-model, and gap-analysis views. | Scenario explorer; kept deployable for existing Vercel projects. |
| `shopworld-platform/` | Python package for deterministic commerce-agent evaluation: seeded state, Shopify-like APIs, tasks, rewards, traces, and reports. | Canonical simulator/evaluation runtime. |
| `platform-rnd/` | Research archive and active planning notes. | Reference only; use `platform-rnd/README.md` to identify active docs. |

The scenario explorers are not separate product directions; they are deployable visual slices that explain workflows the platform should eventually evaluate deterministically. New experiments should either become part of the root demo, land as tested platform scenarios, or remain as clearly labeled research notes under `platform-rnd/`.

## Root web app

The root app is intentionally small. It demonstrates the core evaluation loop without pretending to be the full platform:

- Customer prompts contain intent, budget, and patience constraints.
- The operator picks one fulfillment action from a fixed catalog.
- The state machine scores margin, refunds, reputation, inventory, daily goals, and restocking decisions.
- The signup API can capture interest when Vercel Blob is configured.

### Structure

```text
api/signup.js     Serverless POST endpoint for email capture via Vercel Blob
public/favicon.svg
src/App.jsx       Main demo state machine, screens, restock flow, and signup UI
src/gameData.js   Catalog, customer prompts, scoring rules, restock offers, day goals
src/main.jsx      React entry point
src/styles.css    Design tokens, layout, components, animations
src/ui.jsx        Shared HUD pieces: cash, reputation, patience ring, floaters
support-sim/      Deployable support-workflow scenario explorer
wismo-sim/        Deployable WISMO/order-exception scenario explorer
index.html        Vite HTML shell
vercel.json       Vercel build/output configuration
vite.config.js    Vite React plugin configuration
```

## Platform runtime

`shopworld-platform/` owns the long-term product: reproducible agent evaluation for Shopify-like operations. Its core loop is:

```text
seeded commerce state → agent tool/API actions → world transition → state/trace evaluation → readiness report
```

The platform should prioritize deterministic end-to-end vertical slices over broad but shallow API coverage. Post-purchase support and WISMO-style workflows are the clearest first slice because they tie customer messaging, order state, fulfillment, refunds, inventory, policy, and collateral-damage checks together.

## Canonical commands

Use the root `Makefile` for repeatable checks across both runtimes:

| Command | Purpose |
| --- | --- |
| `make app-build` | Build the Vite app. |
| `make app-dev` | Start the Vite dev server. |
| `make app-preview` | Preview the built Vite app. |
| `make scenario-build` | Build the deployable support and WISMO scenario explorers. |
| `make platform-sync` | Install/sync Python dependencies from `shopworld-platform/uv.lock`. |
| `make platform-test` | Run the Python platform test suite. |
| `make platform-lint` | Run Ruff checks on platform source and tests. |
| `make platform-type` | Run mypy on platform source. |
| `make platform-check` | Run platform tests, linting, and typing. |
| `make check` | Run app build plus all platform checks. |
| `make format` | Format platform Python code with Ruff and Black. |

## Local development

### Web app

```bash
npm install
npm run dev
npm run build
npm run preview
```

### Platform

```bash
cd shopworld-platform
uv sync --frozen --all-extras
uv run pytest tests/
uv run ruff check src tests
uv run mypy src
```

## Email capture

The signup form posts JSON to `/api/signup`:

```json
{ "email": "you@example.com" }
```

The endpoint validates the email, deduplicates by address, and stores entries in a private Vercel Blob object named `signups.json` when `BLOB_READ_WRITE_TOKEN` is available. Without the token, it returns a successful no-op response so local gameplay and deployments without storage do not crash.

## Product guardrails

- Keep the root app as a concise explanation of ShopWorld, not a second product.
- Keep deterministic agent evaluation in `shopworld-platform/`.
- Avoid adding orphan prototype directories; every runnable app needs a documented owner, command, deployment reason, and relationship to the platform.
- Treat `platform-rnd/` as context, not source of truth, unless its index marks a document active.
- Prefer one complete vertical slice with tests and evaluator checks over many partial API mocks.
