Scope the MVP around **WISMO + order modification + returns/refunds + delivery exceptions + disputes**, because that is where Shopify merchants face the highest support volume and the sharpest divide between clean native workflows and app/manual workarounds.

## Research grounding

* **AppWorld pattern to copy:** each task should have a supervisor, instruction, initial state, tool/API surface, and programmatic state-based evaluation; AppWorld reports 9 apps, 457 APIs, ~100 fictitious users, and 750 tasks with state-based unit tests that check both success and collateral damage. ([GitHub][1])

* **Shopify does support basic WISMO, but not full exception management:** customers can track shipments through the order status page, notification emails, and the Shop app after tracking is added; supported carriers can show real-time updates, but unsupported carriers fall back to a carrier link without real-time status/map updates. ([Shopify Help Center][2])

* **WISMO deserves special coverage:** Gorgias reported shipping status, refunds, and damaged orders as top ecommerce customer concerns; Sendcloud cites WISMO as over 35% of support interactions, and AfterShip cites a Mous case where proactive tracking reduced contact rate from 12.9% to 5.9%. Vendor numbers should be treated as directional, not universal benchmarks. ([Gorgias][3])

* **Native Shopify workflows are uneven:** Shopify supports order cancelation, order editing before fulfillment, shipping address updates via `orderUpdate`, returns via `returnCreate`, refunds via `refundCreate`, fulfillment holds, tracking updates, and dispute-evidence updates. ([Shopify Help Center][4])

* **The simulator should expose operational limits:** Shopify says unfulfilled items can be edited, but fulfilled items cannot be removed or quantity-adjusted; returns have status/eligibility constraints; chargebacks have reason-specific evidence requirements. ([Shopify Help Center][5])

## MVP benchmark scope

* **Module name:** `PostPurchaseSupportWorld`.

* **Agent role:** merchant support/operations AI acting on behalf of a Shopify merchant.

* **Core question:** can the agent resolve after-sales issues profitably, safely, policy-compliantly, and with minimal collateral damage?

* **Primary interface:** Shopify-like GraphQL tools plus simulated helpdesk, carrier, warehouse/3PL, returns portal, payment dispute, and customer messaging tools.

* **Evaluation style:** AppWorld-like deterministic state tests, with explicit checks for wrong refunds, inventory corruption, customer overpromises, missed fraud signals, unnecessary escalation, and unresolved customer state.

## MVP use-case set

* **WISMO / “Where is my order?”:** customer asks for order status, ETA, tracking link, carrier delay explanation, or split-shipment status.

* **Late shipment:** order is past promised delivery date; agent must determine whether to apologize only, send tracking, issue shipping refund, open carrier case, reship, or escalate.

* **Cancel order:** agent must determine whether the order is unfulfilled, fulfillable, fulfilled, partially fulfilled, label-created, or already delivered before canceling/refunding/restocking.

* **Change address:** agent must update address if still safe; hold fulfillment if needed; reject or reroute if already shipped.

* **Swap size / variant:** agent must edit order pre-fulfillment or create exchange/return flow post-fulfillment.

* **Return item:** agent must check policy window, condition, final-sale tags, prior refunds, inventory disposition, and RMA state.

* **Partial refund:** agent must compute correct refund amount, tax/shipping handling, restock behavior, and customer notification.

* **Damaged package/item:** agent must collect evidence, distinguish carrier damage from product defect, choose refund/reship/store credit, and create warehouse/carrier feedback.

* **Missing item / wrong item:** agent must compare ordered, fulfilled, packed, shipped, and delivered state; issue replacement/refund only when evidence supports it.

* **Chargeback:** agent must detect dispute reason, assemble evidence, avoid duplicate refund, and submit or escalate before evidence deadline.

* **WISMR / “Where is my return/refund?”:** customer asks about return label, return-in-transit, received return, inspection, refund timing, or exchange shipment.

* **Policy edge case:** outside return window, final sale, international customs delay, suspicious repeat refunds, gift order, or subscription/order created by external app.

## Workflow cleanliness labels

* **L0 — Native clean:** one safe Shopify mutation or admin action resolves the issue.

* **L1 — Native multi-step:** Shopify supports it, but the agent must sequence several actions correctly.

* **L2 — Native data, external action:** Shopify has order/tracking/payment state, but the resolution requires carrier, warehouse, customer, or payment-network action.

* **L3 — App-pattern workflow:** best real-world workflow usually uses a helpdesk, tracking app, returns portal, fraud tool, or claims app.

* **L4 — Human/escalation required:** policy override, legal/payment dispute risk, high-value fraud, ambiguous evidence, or customer threat.

## Use-case cleanliness map

| Use case             |                           Native Shopify baseline | Likely gap/workaround                                             | Simulator priority |
| -------------------- | ------------------------------------------------: | ----------------------------------------------------------------- | -----------------: |
| WISMO basic tracking | Clean if tracking exists and carrier is supported | Poor exception reasoning; unsupported carriers degrade visibility |                 P0 |
| Late shipment        |                                           Partial | Carrier/3PL investigation, proactive recovery policy              |                 P0 |
| Cancel order         |                          Clean before fulfillment | Risk after fulfillment/label creation/partial shipment            |                 P0 |
| Change address       |         Clean before fulfillment via order update | Hold/reroute/manual carrier flow after label/shipment             |                 P0 |
| Swap size            |           Clean before fulfillment via order edit | Return/exchange flow after fulfillment                            |                 P0 |
| Return item          |                                         Supported | Eligibility, RMA, warehouse inspection, fraud                     |                 P0 |
| Partial refund       |                                         Supported | Correct calculation and avoiding duplicate refunds                |                 P0 |
| Damaged package      |                                           Partial | Evidence collection, carrier claim, reship/refund policy          |                 P0 |
| Chargeback           |                    Supported for evidence updates | Evidence quality, deadline, duplicate refund risk                 |                 P1 |
| WISMR                |                                           Partial | Return tracking, inspection, refund timing communication          |                 P1 |

## World model objects

* **Customer:** identity, email/phone, loyalty tier, prior orders, prior complaints, fraud/risk markers, communication tone.

* **Order:** status, financial status, fulfillment status, editability, cancellation eligibility, tags, notes, risk status.

* **Line item:** SKU, variant, quantity, price, tax, discount, fulfillment state, return eligibility, final-sale flags.

* **Fulfillment order:** assigned location, hold state, fulfill-by date, carrier, tracking number, split shipment state.

* **Shipment:** carrier events, ETA, delay reason, exception code, delivered timestamp, proof of delivery.

* **Inventory:** available, committed, reserved, damaged, returned, restocked, quarantined.

* **Return/RMA:** requested items, reason, approval status, label state, received state, inspection result, exchange items.

* **Refund:** amount, method, tax/shipping treatment, restocking, original payment constraints, store credit.

* **Dispute:** reason, deadline, evidence packet, order link, shipping proof, customer communications, status.

* **Policy:** return window, final-sale exclusions, damaged-item policy, refund method, reship threshold, goodwill budget.

* **Support ticket:** channel, intent, sentiment, SLA, customer message history, agent response, resolution state.

## Simulator actors

* **Customer simulator:** asks ambiguous, impatient, or incomplete after-sales questions.

* **Carrier simulator:** emits tracking events, delay codes, delivery exceptions, proof-of-delivery outcomes.

* **Warehouse/3PL simulator:** packs orders, creates labels, ships, receives returns, inspects damaged/wrong/used items.

* **Payment processor simulator:** opens disputes, sets evidence deadlines, resolves chargebacks.

* **Returns portal simulator:** creates RMAs, labels, exchanges, store-credit options, inspection outcomes.

* **Merchant policy engine:** determines what is allowed, discretionary, or prohibited.

* **Evaluator:** checks final state, money movement, inventory movement, customer response, and collateral damage.

## Task template

* **Initial state:** seeded order, customer, inventory, fulfillment, carrier, return, payment, and support-ticket records.

* **Customer instruction:** realistic message such as “I ordered a medium but need a large; can you fix this before it ships?”

* **Hidden facts:** fulfillment already held, label printed, SKU out of stock, customer previously refunded, or package marked delivered.

* **Allowed tools:** Shopify GraphQL, helpdesk reply, carrier lookup/claim, warehouse hold, return portal, payment dispute.

* **Expected resolution:** concrete state transition, not just a good-sounding response.

* **Collateral checks:** no duplicate refund, no impossible promise, no wrong SKU, no negative inventory, no customer PII leakage.

## Golden MVP scenarios

* **WISMO happy path:** tracking exists, supported carrier, ETA available; agent replies with exact status and tracking link.

* **WISMO stale tracking:** no carrier scan for 5 days; agent explains uncertainty, opens carrier check, sets follow-up state.

* **WISMO unsupported carrier:** Shopify shows only carrier URL; agent uses external carrier API or escalates.

* **Cancel before fulfillment:** agent cancels, refunds, restocks, notifies customer.

* **Cancel after shipment:** agent refuses cancelation, explains return path, avoids refunding before return.

* **Address change before fulfillment:** agent updates address and records note.

* **Address change after label:** agent puts fulfillment on hold if possible; otherwise attempts carrier intercept or escalates.

* **Swap size in stock before fulfillment:** agent edits order to new variant and preserves price/payment correctness.

* **Swap size out of stock:** agent offers alternatives without editing to impossible inventory.

* **Return eligible item:** agent creates return/RMA, label, expected refund timeline.

* **Return final-sale item:** agent denies policy exception or escalates based on policy and customer tier.

* **Partial refund damaged item:** agent verifies photo/evidence, refunds correct line-item amount or reships.

* **Missing item split shipment:** agent detects second fulfillment still in transit and avoids unnecessary refund.

* **Delivered-not-received:** agent checks proof of delivery, risk, carrier claim eligibility, reship/refund threshold.

* **Chargeback product not received:** agent assembles tracking, delivery proof, customer communication, and policy evidence.

## Metrics

* **Task success:** correct final operational state.

* **Financial accuracy:** refund/store-credit/reship cost equals policy and facts.

* **Inventory accuracy:** stock, restock, quarantine, exchange, and replacement states remain consistent.

* **Customer correctness:** response contains true status, no overpromise, no unsupported claim.

* **Policy compliance:** return window, final sale, fraud, goodwill, and escalation rules followed.

* **Workflow cleanliness:** L0–L4 classification matched and justified.

* **SLA performance:** issue resolved or escalated within simulated service window.

* **Collateral damage:** no duplicate refund, wrong cancelation, wrong address, privacy leak, or chargeback evidence miss.

## MVP build plan

* **Phase 1 — Deterministic Shopify-like core:** implement orders, line items, fulfillment orders, tracking, returns, refunds, disputes, inventory, and tickets.

* **Phase 2 — 100 seeded tasks:** 40 WISMO/late/delivery, 20 cancel/address/edit, 20 return/exchange/refund, 10 damaged/missing/wrong item, 10 chargeback/fraud.

* **Phase 3 — Workflow cleanliness evaluator:** label every task L0–L4 and produce merchant-facing diagnosis: “native clean,” “native but brittle,” “needs app,” or “manual escalation.”

* **Phase 4 — Synthetic customer variation:** same backend facts with different customer phrasings, incomplete information, anger, multilingual fragments, and wrong order numbers.

* **Phase 5 — Merchant benchmark report:** score agents by resolution rate, refund leakage, customer correctness, escalation judgment, and app/manual-workaround recognition.

## Recommendation

* **Make WISMO the anchor vertical.** It is frequent, easy to simulate, visibly valuable to merchants, and exposes the real gap between “Shopify has an order status page” and “the merchant can reason through delivery exceptions.”

* **Do not build only a returns simulator.** Returns matter, but the broader after-sales operating loop is WISMO → exception → modification → return/refund/exchange → dispute prevention.

* **Use “workflow cleanliness” as the commercial wedge.** Merchants will care less about abstract agent scores and more about: “Can AI handle this safely in my store today, or do I need Loop/AfterShip/Gorgias/ReturnGO/manual ops?” Loop’s positioning itself spans tracking, editing, returns, exchanges, fraud prevention, and shipping, which validates the bundle as an operational category rather than a single support intent. ([loopreturns.com][6])

[1]: https://github.com/StonyBrookNLP/appworld?utm_source=chatgpt.com "AppWorld: A Controllable World of Apps and People for ..."
[2]: https://help.shopify.com/en/manual/fulfillment/setup/order-status-page/order-tracking "Shopify Help Center | Order tracking at Shopify"
[3]: https://www.gorgias.com/blog/customer-experience-insights-2023 "Ecommerce Customer Experience in 2023: Insights & What’s Next in 2024"
[4]: https://help.shopify.com/en/manual/fulfillment/managing-orders/canceling-orders "Shopify Help Center | Canceling orders"
[5]: https://help.shopify.com/en/manual/fulfillment/managing-orders/editing-orders/considerations "Shopify Help Center | Considerations for editing orders"
[6]: https://www.loopreturns.com/ "Loop Returns | The Operations Platform Built for Retention"

