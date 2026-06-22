# Phase 2 — Live Backend Design (for review)

_A hosted backend that turns the static explainer into an interactive proving ground._
_Status: DRAFT for review. Do not execute until approved. Last updated: 2026-06-22._

## What Phase 2 unlocks that Phase 1 cannot

Phase 1 ships pre-computed evidence: a fixed report, fixed traces. It answers "what did the benchmark find?" It cannot answer the questions a serious buyer asks next:

- "Run *my* scenario." — submit a ticket/workflow, watch both agents handle it live.
- "Run it against *my* store." — import their catalog/order shapes and evaluate on data they recognize.
- "Let me drive." — step an agent through a scenario, change the policy, see the outcome shift.
- "Show me the leaderboard." — third-party agents submitted and ranked, which is the credibility flywheel.

These require executing Python (the simulator + agents) on demand. That is a backend. This document is the design to review before we build it.

## Decision this document is asking for

Approve (a) building a backend at all, (b) GCP as the host, and (c) the scope tier below (start at Tier 1). Everything past Tier 1 is optional and sequenced.

## Architecture

```text
Browser (Vercel static FE, from Phase 1)
        │  HTTPS / JSON
        ▼
API Gateway / Cloud Load Balancer
        │
        ▼
FastAPI service  ──────────────►  Job queue (Cloud Tasks / Pub-Sub)
(Cloud Run)                              │
        │                                ▼
        │                       Benchmark worker (Cloud Run job / GKE)
        │                       = shopworld-platform + milli_run + llm_agent
        │                                │
        ▼                                ▼
  Postgres (Cloud SQL)            Object store (GCS)
  - runs, scenarios, users        - full traces, results.json artifacts
        ▲                                │
        └────────────── reads ───────────┘
```

The platform already has the right seam: `shopworld-platform/src/shopworld/serve/` exists (currently empty) and the package is structured as an importable library with a clean `Agent` protocol and a neutral runner. Phase 2 wraps that library in an HTTP service — it does not rewrite it.

## Why GCP (and the honest alternative)

GCP fits because the workload is bursty, stateless-per-job Python, and we want managed Postgres + object storage + a queue without ops overhead. **Cloud Run** scales to zero between demos (cost ≈ $0 idle, which matters for a pre-revenue tool) and handles the request tier; **Cloud Run jobs** or a small **GKE** pool run the actual benchmark episodes off the request path. **Cloud SQL** (Postgres) for run metadata, **GCS** for trace artifacts, **Cloud Tasks/Pub-Sub** for the queue.

Honest alternative: none of this is GCP-specific. The same shape runs on AWS (Fargate + RDS + S3 + SQS) or Fly.io/Render for a smaller footprint. Recommendation: pick GCP only if there's an existing GCP relationship or credits; otherwise the cheapest path to Tier 1 is a single container on Cloud Run / Fly with SQLite-or-managed-Postgres and GCS-or-equivalent. Don't over-build the control plane before there's load.

## Scope tiers (sequence them)

**Tier 1 — Hosted live run (the minimum that justifies a backend).**
- One endpoint: `POST /run` with `{scenario_id | inline_scenario, agents[], seed}` → enqueues, returns `run_id`.
- `GET /run/{id}` → status + result + trace, same JSON shape Phase 1 already renders.
- Runs the existing 30-scenario set or a single scenario on demand. No store import, no auth beyond a rate limit.
- Frontend: a "Run it live" button on the result section that streams a fresh episode instead of replaying a baked one.
- This alone converts the meeting demo from "here's what we found" to "watch it happen now."

**Tier 2 — Bring-your-own scenario.** Authenticated users submit a ticket + policy + initial state through a guarded form; the service validates it into a `Task` and runs both agents. Needs auth (Google/email), input validation, and abuse limits (this executes code paths on our infra). High sales value: a prospect's own edge case, scored live.

**Tier 3 — Store-data import.** Map a customer's catalog/order export into ShopWorld's seeded-state generator (`generate/`) so evaluation runs on data they recognize. Largest trust unlock, largest effort and data-handling/compliance surface. Gate behind a signed agreement; treat customer data as sensitive (encryption at rest, retention policy, deletion).

**Tier 4 — Public leaderboard.** Third parties submit agents against a frozen scenario set through the neutral runner; ranked results published. This is the credibility flywheel and the long-term moat, but only worth building once Tiers 1–2 prove demand. Requires sandboxed execution of untrusted agent code — a real security project (gVisor/Firecracker isolation, resource caps, network egress lockdown). Do not start here.

## Hard requirements regardless of tier

- **Preserve the neutrality invariant.** The runner imports no agent under test; agents reach ShopWorld only through the Merchant API Surface. The service must not leak this seam — no endpoint exposes canonical DB, ground truth, evaluator logic, or rewards. This is the property that makes results credible; protect it in the API layer.
- **Determinism survives hosting.** Same seed + actions = same result must hold across workers. The platform already threads an episode-local RNG; the service must pass seeds explicitly and never rely on wall-clock or global state.
- **Cost control.** Cap concurrent episodes, cap per-run wall time, scale request tier to zero when idle. A runaway LLM-agent loop is a billing event — enforce step and token budgets server-side.
- **Artifact parity.** The live JSON must match the Phase 1 static schema so the same frontend components render both. Build Phase 1's `benchmark.json` schema to be forward-compatible with Tier 1's live response.

## Rough effort / sequencing

- Tier 1: small — wrap the existing library in FastAPI, one queue, one worker, deploy. Days, not weeks, because the engine is done.
- Tier 2: medium — auth, validation, abuse controls.
- Tier 3: medium-large — data mapping + compliance.
- Tier 4: large — untrusted-code sandboxing + leaderboard ops.

## Recommendation

Approve Tier 1 only, now. It is the highest demo-value, lowest-risk increment and reuses the tested engine almost wholesale. Defer Tiers 2–4 until Phase 1 is live and a real prospect asks for one of them by name — let demand pull scope rather than building the leaderboard before anyone has run a single live episode. Revisit this doc after the first three stakeholder meetings; their asks should decide whether Tier 2 or Tier 3 comes next.

---

**TL;DR.** The engine is already a clean importable library with an empty `serve/` seam waiting for it. Phase 2 = wrap it in FastAPI on Cloud Run, queue episodes to a worker, store traces in GCS, and add a "run it live" button. Approve Tier 1 (hosted live run) now; let stakeholder demand decide Tiers 2–4. Protect the neutrality and determinism invariants in the API layer — they are the credibility, and they're easy to leak.
