# ShopWorld × milli.run — Stakeholder Narrative

_For meetings with Salsify, Mars, and Family Mart. One story, three accents._
_Last updated: 2026-06-22._

## The one-sentence version

Before any business lets an AI agent touch live commerce systems, someone has to prove the agent is safe — and today nobody can. ShopWorld is the proving ground; milli.run is the agent that passes it.

## Problem

Every commerce org is being sold AI agents. None of them can answer the only question that matters before granting write access: *what does this agent break when it's wrong?* Demos show the happy path. Production shows the refund issued to a fraudster, the address changed on an already-shipped order, the inventory corrupted, the abuse ticket that should have escalated and didn't. There is no standard, reproducible way to measure that downside before it hits a real customer or a real ledger.

## Why this is unsolved

LLM agent vendors benchmark on task success — "did it answer the question." That metric hides collateral damage, the thing operators actually fear. Generic agent benchmarks (AppWorld and similar) test office automation, not commerce state: orders, fulfillment, refunds, policy windows, fraud signals, authority scopes. And a chat transcript is not evidence — an operator can't audit a vibe. The gap is a neutral environment that holds hidden truth, scores the full consequence of an action, and produces an audit trail an operator can sign off on.

## What we built

Two things, both real and tested, not slideware.

**ShopWorld** — a deterministic simulator of a Shopify-like merchant business. Seeded store state, hidden world physics (customer patience, fraud risk, carrier reliability, demand), a 25-tool Merchant API Surface that is the *only* way an agent can act, and a hidden evaluator that scores success, collateral damage, policy violations, business impact, and recommends a safe authority level (read-only → draft → supervised → autonomous). ~11,500 lines of Python, 197 passing tests. Agents never touch the database, ground truth, or the scorer — the same separation that makes a benchmark credible.

**milli.run** — a neuro-symbolic merchant agent under test: shallow NLU intent classifier, entity extraction, a confidence router, explicit policy/risk guards, workflow state machines, and a transaction planner with rollback and a full audit log. It is deliberately *not* an LLM. It trades open-ended language ability for determinism, hard guards, and auditability.

We ran both against an LLM agent on the same scenarios through the same tool surface. The benchmark runner is neutral — it imports neither agent under test and reports empirical outcomes.

## The receipt

30 scenarios × 3 seeds = 270 episodes. Six workflow families (WISMO, cancellation, address change, refund, return, escalation/abuse).

| Agent | Success | Avg score | Collateral damage | Held-out NLU accuracy |
| --- | --- | --- | --- | --- |
| Baseline (does nothing useful) | 60% | 56 | 0 | — |
| LLM agent | 83% | 70 | 0 | — |
| **milli.run** | **100%** | **80** | **0** | **94%** |

The LLM agent's failures are not random — 15 of them cluster in one bin: `policy_drift`. It fails to escalate legal-threat and chargeback-threat tickets, or refunds without a policy check. milli.run has zero failures on this set and logs every decision with its cause and a rollback plan.

The story is not "symbolic beats LLM." The story is "you can finally see the difference, scored and audited, before it costs you anything." That neutrality is the product.

## Business impact (the translation layer)

- **De-risks AI adoption.** The blocker to commerce-agent adoption is trust about write access, not capability. ShopWorld converts "we're nervous" into a readiness report with a specific authority recommendation per workflow.
- **Quantifies downside, not just upside.** Collateral-damage scoring puts a number on the wrong-refund / inventory-corruption / missed-escalation risk that operators carry today as unmeasured fear.
- **Auditable by non-engineers.** Every milli.run decision has a cause and a rollback plan. An ops or risk leader can read the trace, not trust a vibe.
- **Reproducible.** Same seed + same actions → identical outcome. Procurement, risk, and compliance can re-run the exact evaluation.

## One story, three accents

The spine is identical for all three: *neutral proving ground + auditable agent = safe path to commerce automation.* Adjust only the lead example.

**Salsify (commerce experience / product data platform).** Lead with the platform angle: ShopWorld is the QA layer their ecosystem lacks. As Salsify's customers push product content and commerce workflows toward agents, Salsify can offer evaluation evidence as a trust feature — "agents validated against ShopWorld before they touch your catalog/orders." Accent: structured-data reliability, ecosystem trust, white-label/partner potential. The deferred shopper-facing benchmark (catalog reasoning over dirty product data) is the natural second act for them — flag it as roadmap, not vapor.

**Mars (global CPG brand owner).** Lead with brand safety at scale. Mars doesn't run one store; it runs commerce across thousands of retail surfaces. The fear is an agent making a brand-damaging or financially wrong decision at scale with no audit trail. Accent: collateral-damage scoring as brand-risk insurance, the escalation/abuse family (a mishandled legal-threat ticket is a brand event), and reproducibility for governance. Frame milli.run's audit log as the thing that survives a post-incident review.

**Family Mart (convenience retailer / operator).** Lead with cost-to-serve and customer experience. High-volume, thin-margin, support-heavy operations where WISMO and refunds dominate ticket load. Accent: the WISMO/cancellation/refund families directly mirror their support queue; the readiness report tells them which workflows are safe to automate now vs. keep human-supervised. Frame it operationally: "automate the 80% that's safe, prove it, keep humans on the 20% that isn't."

## What to show in the room

1. The comparative table above — one slide, the whole thesis.
2. A live or recorded scenario explorer (WISMO / support) so they *feel* the granular decisions an agent gets wrong.
3. One milli.run audit trace next to one LLM `policy_drift` failure, side by side. That contrast closes the meeting.

## What's true vs. what's roadmap (say this plainly — credibility is the asset)

- **Built and tested:** the simulator, the 25-tool surface, six workflow families, both agents, the neutral runner, the comparative report, 197 passing tests.
- **Roadmap:** the shopper-facing product-discovery benchmark (catalog reasoning, ~40% of the original design) is deliberately deferred until the merchant benchmark ships its first external report. Importing a customer's real store data, a public leaderboard, and a hosted interactive run are Phase 2 (see `PHASE2_BACKEND.md`).

Underclaiming wins these rooms. The 100% / 0-collateral number is strong enough that it invites scrutiny — meet it with "here are the 270 reproducible episodes and the test suite," not with bigger adjectives.

---

**TL;DR.** Commerce orgs can't safely adopt agents because nobody measures what an agent breaks when it's wrong. ShopWorld is a neutral, deterministic, auditable proving ground that does. milli.run passes it at 100% with zero collateral damage and a full audit trail; the LLM agent drifts on policy/escalation. Same story for Salsify, Mars, and Family Mart — change the opening example, not the spine.
