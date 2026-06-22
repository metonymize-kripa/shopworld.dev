# ShopWorld: A Realistic Ecommerce Environment for Benchmarking Shopify Merchant Agents

*Working title. Audience: Shopify merchants who are AI-curious but haven't committed to agents. Goal: give them a safe environment to stress-test an agent before touching a live store.*

---

## Problem

Merchants can't evaluate an AI agent against their store without risking real orders, customers, and supplier relationships. Sandboxes exist but are thin: they let you test individual API calls, not the multi-step judgment calls that actually matter (reorder before a stockout, respond to a supplier delay, decide whether a refund complaint is legitimate). The result is that adoption stalls at "demo in a controlled environment" and never reaches "I trust this on Monday morning."

## Why

The evaluation gap is structural. AppWorld [1] proved that realistic multi-app environments catch failure modes that single-API tests miss — GPT-4o solves ~49% of normal tasks and ~30% of challenge tasks in a simulated world, versus near-100% on synthetic API-call sequences. τ-bench [2] and τ²-bench [3] narrowed this to customer service agents across airline and retail: even SOTA models fail at consistency (pass^k drops sharply as k increases). Neither exists in Shopify's operational context, where the merchant agent must simultaneously manage inbound demand signals, supplier constraints, logistics status, and ad spend — not just respond to a customer query.

## What ShopWorld Is

**ShopWorld Engine** is a stateful simulation of a Shopify store's operating environment. It wraps the Shopify GraphQL Admin API in a deterministic replay layer and populates the world with synthetic actors — suppliers, carriers, customers, browsers, ad platforms — that generate realistic inbound events. The agent under evaluation plays the role of a store manager or merchant: it receives these events and acts on the store via the same API surface a real integration would use.

**ShopWorld Benchmark** is the task suite layered on top: 500+ structured scenarios with programmatic evaluation (state-based + action-based unit tests, following τ-bench's pass^k methodology [2]).

Target market: Shopify merchants who want to see what an AI agent can actually do before deploying it. Not researchers. Not Shopify engineers. A merchant who sells $2M/year in DTC apparel and is wondering whether to trust an agent to handle replenishment.

---

## Architecture

### The Simulated World

ShopWorld populates a synthetic store with enough state to make agent decisions non-trivial. The store starts from a configurable seed (product catalog size, AOV range, sales velocity, supplier lead times, margin targets) and is optionally bootstrapped from real store data via a one-time GraphQL export.

**Synthetic actor classes:**

- *Suppliers.* Each has a lead time distribution, MOQ, stockout behavior, and occasional failure modes (delayed shipment confirmation, invoice discrepancy, sudden price change).
- *Logistics providers.* Generate tracking events, exception states (lost package, customs hold, address invalid), and SLA windows. Mapped to Shopify's `FulfillmentOrder` and `Fulfillment` objects.
- *Customers with complaints.* Drawn from a distribution of complaint types weighted by category: WISMO (where is my order), wrong item, damaged, refund request, chargeback threat. Each has a simulated patience window before escalation.
- *Shoppers and browsers.* Generate storefront traffic, cart abandons, and conversion signals via the Storefront API. Used to test demand-sensing and markdown decisions.
- *Advertising venues.* Simulate Meta/Google campaign performance signals: ROAS, CPM shifts, frequency cap hits. Agent can act on these to adjust budgets or pause campaigns via simulated ad platform connectors.

All actors emit events on a simulated clock. The agent can run in real-time mode (events arrive asynchronously) or turn-based mode (process one event at a time, deterministic for evals).

### Shopify API Coverage

ShopWorld wraps the Shopify GraphQL Admin API 2026-04. Coverage is prioritized by operational frequency, not schema completeness. The goal is to cover the endpoints a merchant automation agent will hit on a busy Tuesday, not every edge in the schema.

**Tier 1 — core operational loop (must work correctly for any useful agent):**

| Domain | Key Queries / Mutations |
|---|---|
| Orders | `orders`, `order`, `orderUpdate`, `orderCancel`, `draftOrderCreate`, `draftOrderComplete` |
| Fulfillment | `fulfillmentOrders`, `fulfillmentCreate`, `fulfillmentOrderMove`, `fulfillmentOrderHold` |
| Inventory | `inventoryLevels`, `inventoryAdjustQuantities`, `inventoryBulkAdjustQuantityAtLocation` |
| Products & Variants | `products`, `productUpdate`, `productVariantUpdate`, `productVariantsBulkUpdate` |
| Customers | `customers`, `customer`, `customerUpdate` |
| Returns & Refunds | `returns`, `returnCreate`, `refundCreate`, `orderRefund` |

**Tier 2 — high-value automation targets:**

| Domain | Key Queries / Mutations |
|---|---|
| Purchase Orders | `purchaseOrders`, `purchaseOrderCreate`, `purchaseOrderUpdate` (B2B / Supplier API) |
| Metafields | `metafieldsSet`, `metafieldDelete` (custom supplier SKU mapping, reorder thresholds) |
| Price Rules & Discounts | `priceRuleCreate`, `discountCodeCreate`, `automaticDiscountCreate` |
| Webhooks | `webhookSubscriptionCreate` (agent self-configures event subscriptions) |
| Analytics | `shopifyqlQuery` (sales velocity, margin signals for reorder decisions) |

**Tier 3 — covered for completeness, tested less aggressively:**

Collections, marketing activities, B2B catalogs, gift cards, checkout profile mutations.

ShopWorld ships a mock Shopify GraphQL server that returns deterministic responses keyed to the simulated world state. The agent never touches a real store during eval.

### Evaluation

**Metric: pass^k** — following τ-bench [2], the fraction of tasks an agent completes correctly across k independent trials of the same scenario. k=1 for normal tasks, k=3 for challenge tasks. This surfaces consistency failures that a single pass misses.

**State-based grading:** After each scenario, the simulator checks world state against an annotated goal state. "Inventory for SKU-4821 is above the reorder point," "customer complaint #7 resolved with refund, no chargeback," "order #302 fulfilled within SLA window." Checks tolerate different valid paths to the same goal — an agent that reorders via PO vs. manual inventory adjustment both pass if the outcome is correct.

**Action-based grading (secondary):** For scenarios where sequencing matters (e.g., don't send a fulfillment confirmation before the carrier has a tracking number), action order is also checked.

**Collateral damage checks:** Borrowed from AppWorld [1]. After each scenario, the simulator checks that the agent didn't change things it wasn't supposed to: no price changes outside authorized scenarios, no unintended bulk cancellations, no customer emails sent outside the task scope.

---

## Task Taxonomy

Tasks are grouped by operational domain and complexity tier.

**Replenishment & Inventory**
- Normal: reorder a SKU that crossed its threshold, given supplier lead time and current velocity.
- Challenge: reorder decision with a concurrent supplier delay signal and a competing low-margin SKU that's also near threshold, with a fixed PO budget.

**Order Operations**
- Normal: process a batch of fulfillment orders, route to correct location, generate pick list.
- Challenge: order split across two locations where one is understocked; decide whether to hold, split ship, or substitute variant.

**Customer Complaint Resolution**
- Normal: WISMO query, carrier has tracking event, compose update.
- Challenge: lost package, carrier exception, no tracking event in 7 days, customer threatening chargeback. Decide: reship vs. refund vs. wait, within store policy.

**Pricing & Promotions**
- Normal: create a discount code for a segment, set expiry, validate it doesn't stack with an existing automatic discount.
- Challenge: flash sale decision based on real-time ROAS signal and remaining inventory; agent must not discount below cost.

**Supplier Coordination**
- Normal: confirm a PO receipt, reconcile invoice against PO, flag a line-item discrepancy.
- Challenge: supplier sends a partial shipment with no ETA for the remainder; reorder point is still breached; decide whether to source from secondary supplier at higher cost.

**Returns & Fraud**
- Normal: process a legitimate return, issue refund, restock item.
- Challenge: return request on an order flagged by Shopify's fraud analysis; decide whether to approve, require photo verification, or deny.

---

## Synthetic Data Pipeline

ShopWorld ships with a default synthetic catalog seeded from public e-commerce datasets (Open Images product taxonomy, publicly available supplier lead time distributions from supply chain research, synthetic customer complaint corpora). All data is fully synthetic — no PII, no real store data.

**Customization loop (the hill-climbing story for merchants):**

1. Merchant exports their store's product catalog, historical order velocity, and supplier list via a one-time GraphQL export script. No ongoing store access required.
2. ShopWorld's data generator fits a store-specific model: category-level velocity, seasonal curves, complaint rate by product type, supplier reliability scores.
3. Eval runs with store-specific scenarios. Agent scores reflect performance on *this merchant's operational reality*, not a generic retail distribution.
4. Merchant sees where the agent fails. They can add custom scenarios targeting those failure modes, tag them with difficulty, and run targeted evals.

The pipeline is explicit: no agent ever writes to the merchant's real store during this process. The export is read-only. The eval runs entirely in the simulator.

---

## Benchmark vs. Training Mode

ShopWorld ships two modes.

**Eval mode** (default): fixed task splits, deterministic world seeds, pass^k scoring, leaderboard-compatible output. Use this to compare agent versions or compare vendors.

**Gym mode**: exposes an OpenAI Gym-compatible interface (`AgentGymEnv`). Reward signal is configurable: task completion, collateral damage penalty, latency, API cost (measured in Shopify cost points). Use this for RL fine-tuning or prompt optimization via hill-climbing. Borrowed from τ²-bench's gymnasium interface [3].

---

## What Success Looks Like for the Target User

A merchant running ShopWorld should be able to answer three questions within an afternoon:

1. Can this agent handle my top-3 operational headaches without making things worse?
2. What's its failure rate on the edge cases that actually show up in my store?
3. If I give it write access to orders and inventory, what's the blast radius when it gets it wrong?

ShopWorld answers all three without touching a live store.

---

## Open Questions / Design Decisions Needed

- *Storefront API coverage:* Include simulated browse/cart events as signals for the agent, or keep the agent scoped to Admin API only? Including the storefront makes demand-sensing tasks tractable but complicates the mock server.
- *Ad platform connectors:* Simulate via a stub or integrate with Meta/Google sandbox APIs? Stubs are faster to ship; real sandboxes add credibility but increase setup friction for merchants.
- *Multi-agent topology:* Should ShopWorld support evaluating a team of agents (e.g., a replenishment agent + a customer service agent) or only a single merchant agent? Single-agent is simpler to eval; multi-agent is closer to how production deployments will look.
- *Leaderboard scope:* Public leaderboard (models compete on a shared eval set) vs. private benchmarking (each merchant's eval is scoped to their store seed). Both are useful; public leaderboard drives model vendor adoption, private benchmarking drives merchant adoption.

---

## TL;DR

ShopWorld is AppWorld for Shopify: a stateful simulation of suppliers, logistics, customers, and ad venues, with the Shopify GraphQL Admin API as the action surface. The agent under eval plays a merchant. Scenarios are graded on pass^k with collateral damage checks. Merchants can seed the simulator from their real store data to get evals that reflect their actual operational context, not a generic retail distribution.

---

**References**

[1] Trivedi et al. (2024). "AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents." ACL 2024 Best Resource Paper. https://arxiv.org/abs/2407.18901

[2] Yao et al. (2024). "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains." arXiv:2406.12045.

[3] Barres et al. (2025). "τ²-bench: Evaluating Conversational Agents in a Dual-Control Environment." arXiv:2506.07982.

[4] Shopify GraphQL Admin API 2026-04 reference. https://shopify.dev/docs/api/admin-graphql/latest