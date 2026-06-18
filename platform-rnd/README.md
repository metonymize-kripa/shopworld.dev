# Platform R&D index

_Date reviewed: 2026-06-18_

`platform-rnd/` contains research notes, implementation plans, and review outputs for the ShopWorld platform. These documents are useful context, but not every file is an active implementation contract.

## Current active references

| Document | Status | How to use it |
| --- | --- | --- |
| `repo-code-review-critical-analysis.md` | **Active review / roadmap input** | Use for prioritizing repository reliability, platform vertical-slice work, API consolidation, and app hardening. |
| `shopworld-product-research-implementation-plan.md` | **Active product context** | Use for product thesis, evaluation positioning, and phased platform planning. |
| `GPT5.5-spec-plan.md` | **Active technical planning context** | Use as a candidate technical spec where it agrees with the current code and review roadmap. |
| `shopify-graphql-api-overview-gpt-5.5.md` | **Reference** | Use for Shopify Admin GraphQL fidelity requirements; validate claims against implementation/tests before treating as complete. |

## Historical or alternative design inputs

| Document | Status | Notes |
| --- | --- | --- |
| `appworld-to-shopworld-gpt5.5.md` | Historical/alternative | Migration inspiration from AppWorld-style environments. |
| `appworld-to-shopworld-claude.md` | Historical/alternative | Parallel migration proposal; reconcile with active specs before implementation. |
| `rle-spec-claude.md` | Historical/alternative | Reinforcement-learning environment ideas that may overlap with active plans. |
| `amazon_toggle_plan.md` | Backlog idea | Treat as speculative until prioritized. |
| `shopworld-business-gtm-research-questions.md` | Business research backlog | Open GTM questions rather than implementation requirements. |
| `germini-starter-doc.txt` | Raw notes | Preserve for context only. |
| `prompts.txt` | Raw prompt archive | Not a source of product truth. |
| `shopworld_poster_streamlined.html` | Presentation artifact | Demo/communication asset only. |

## Architecture decisions made

- The repository is intentionally a monorepo with two workstreams: the Drop Day Vite app and the Python ShopWorld platform.
- Drop Day remains a compact public-facing demo/marketing app; the Python package owns deterministic agent evaluation.
- `shopworld-platform/src/shopworld/apps/shopify_admin/graphql_api/` should become the canonical Shopify-like GraphQL implementation; older overlapping modules should be deprecated only after behavior is migrated and tested.
- Platform implementation should prioritize one deterministic end-to-end simulator/evaluation vertical slice before adding more API breadth.

## Open questions

- What is the canonical task scenario format for MVP: JSON fixtures loaded by `TaskLoader`, Python-defined task factories, or both with one compatibility layer?
- Which first vertical slice should be made fully executable: WISMO support, inventory replenishment, fulfillment delay, or pricing/promotion?
- What minimum evaluator report should gate agent readiness: task success only, collateral-damage checks, policy violations, business metrics, or all of these?
- What storage primitive should replace the current read/modify/write signup Blob flow before a public launch with meaningful traffic?

## Next review date

Reconcile this index after the first executable platform vertical slice lands, or by **2026-07-18**, whichever comes first.
