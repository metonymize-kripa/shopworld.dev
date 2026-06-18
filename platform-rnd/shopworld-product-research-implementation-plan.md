# ShopWorld Product Research and Implementation Plan

## 1. Executive Summary

ShopWorld is a deterministic reinforcement learning and evaluation environment for AI agents that operate a Shopify merchant business. The agent is evaluated as a store owner or store manager with bounded authority over customer support, inventory, fulfillment, catalog operations, promotions, supplier coordination, advertising, and Shopify Admin GraphQL actions.

The core product thesis is:

> Can an AI safely operate meaningful parts of a small Shopify store before a merchant grants it live write access?

The useful foundation from AppWorld is not its consumer-app benchmark content. The reusable asset is the deterministic, stateful benchmark kernel: resettable world state, typed APIs, task-specific initial states, programmatic evaluators, execution logs, and replayable agent loops.

ShopWorld should use that pattern to build a commerce control environment where actions have delayed business consequences. Refunds reduce cash. Discounts change margin and shopper behavior. Supplier failures create future stockouts. Carrier delays create complaints. Poor customer-service decisions affect reviews, chargebacks, and repeat purchase probability.

The output is not just a benchmark. It is a merchant-facing readiness system that answers:

1. What workflows can this agent perform safely?
2. What permission scopes should the merchant grant?
3. What is the expected uplift and downside risk before deployment?

## 2. Source Synthesis

### 2.1 Inputs Reviewed

- `prompts.txt`: original framing around an AppWorld-style Shopify RLE, merchant/store-manager agent, realistic simulated environment, Shopify GraphQL coverage, synthetic data, store customization, and AI-curious Shopify merchants.
- `rle-spec-claude.md`: concise product spec emphasizing merchant trust, simulated Shopify world, task taxonomy, pass^k evaluation, collateral-damage checks, synthetic data, and eval/gym modes.
- `appworld-to-shopworld-claude.md`: AppWorld reuse analysis: keep engine, evaluator, API docs, common utilities, app framework, MCP serving, and generators; delete bundled app/task content.
- `appworld-to-shopworld-gpt5.5.md`: detailed AppWorld-to-ShopWorld refactor map, new repo structure, MVP cut line, training loop, counterfactual generator, and staged authority commercialization model.
- `GPT5.5-spec-plan.md`: expanded integrated product spec covering target user, agent role, world model, customer service loop, Shopify GraphQL surface, architecture, scenario library, metrics, synthetic data, and implementation sequencing.
- `germini-starter-doc.txt`: conceptual synthesis of AppWorld execution-grounding with tau-bench/tau2-style conversational compliance, Gym-style environment loop, curriculum tiers, RL training methods, and diagnostics.

### 2.2 Unifying Product Direction

The strongest coherent direction is:

- Build a simulated Shopify operating world, not a thin Shopify API mock.
- Make customer service the primary observable symptom of operational quality.
- Use Shopify Admin GraphQL as the primary action surface.
- Include synthetic actors for customers, shoppers, suppliers, carriers, ad venues, and merchant policy supervision.
- Evaluate both final state and action trace.
- Penalize collateral damage and policy violations as first-class outcomes.
- Produce merchant-facing readiness reports by workflow class and permission scope.
- Start with a clean-room ShopWorld core inspired by AppWorld, rather than depending on AppWorld’s encrypted app/task content.

## 3. Product Definition

### 3.1 Product Name

Working name: **ShopWorld**

### 3.2 Product Category

- Agent evaluation environment
- Reinforcement learning environment
- Synthetic commerce simulator
- Merchant readiness and safety assessment platform

### 3.3 Primary User

The initial user is a Shopify merchant who is curious about AI agents but does not yet trust them with live store authority.

Best-fit merchant profile:

- Annual revenue high enough that operational mistakes matter.
- Team small enough that automation pressure is real.
- Existing pain in customer support, fulfillment exceptions, replenishment, catalog hygiene, promotions, or supplier coordination.
- Unclear whether current agents are reliable enough for production write access.

### 3.4 Secondary Users

- Shopify agencies evaluating agent products for clients.
- Commerce-agent startups needing training and evaluation infrastructure.
- Shopify app developers building AI workflows around Admin API actions.
- Model providers demonstrating safe tool use in commerce operations.

### 3.5 Core Promise

ShopWorld lets a merchant stress-test an AI store manager in a private simulated clone before granting live store access.

The merchant should be able to answer, within one afternoon:

1. Can the agent handle my top operational headaches?
2. Where does it fail on my edge cases?
3. What is the blast radius if I grant specific write permissions?
4. Which workflows should stay read-only, draft-only, or supervised?
5. What business upside is plausible under bounded automation?

## 4. Product Thesis

### 4.1 Why Existing Benchmarks Are Insufficient

Single-API and static tool-use benchmarks test whether an agent can call tools correctly. They do not test whether the agent can run a business.

Shopify operations require coupled reasoning across:

- Customer emotion and policy.
- Inventory and fulfillment status.
- Supplier lead times and defects.
- Discounts, margin, and cash.
- Advertising performance and demand shocks.
- API scopes, pagination, throttling, and mutation semantics.
- Long-horizon effects such as refund abuse, stockouts, customer churn, and support backlog.

### 4.2 Why AppWorld Is the Right Kernel Pattern

AppWorld demonstrates a reusable benchmark architecture:

- Resettable stateful world.
- Typed APIs.
- Task-specific initial states.
- Agent execution loop.
- Programmatic evaluation.
- Collateral-damage checks.
- Logs and replay.

For ShopWorld, AppWorld’s consumer apps and benchmark data should be discarded. The reusable idea is the execution-grounded sandbox and evaluator architecture.

### 4.3 Why Tau-Bench and Tau2 Are Relevant

Tau-bench-style environments add multi-turn user interaction and policy compliance. ShopWorld should combine this with AppWorld-style database-state evaluation.

The result is a dual-control environment:

- Agent actions update the world.
- Simulated users and external actors also update the world.
- Rewards evaluate final database state, interaction history, policy compliance, and collateral damage.

### 4.4 Why Andon/Luna Is Relevant

The Andon/Luna inspiration is autonomy under real commercial constraints: inventory, money, vendors, customer expectations, and operational risk.

ShopWorld should simulate this autonomy before a real merchant grants it.

## 5. World Model

### 5.1 World Model Principle

The world model is the moat. A useful RLE must make actions produce realistic delayed consequences.

The environment should model commerce as a coupled system:

```text
observe event/state
→ infer customer, operational, and financial risk
→ choose tool action or message
→ update visible store state
→ update hidden actor state
→ advance simulated time
→ generate exogenous events
→ score business, service, operational, API, and safety outcomes
```

### 5.2 Visible Store State

The simulated Shopify twin should include:

- Products.
- Variants.
- SKUs.
- Inventory items.
- Locations.
- Inventory levels.
- Orders.
- Fulfillment orders.
- Fulfillments.
- Customers.
- Tags.
- Metafields.
- Collections.
- Discounts.
- Abandoned checkouts.
- Refunds.
- Returns.
- Support tickets.
- Cash ledger.
- Supplier purchase orders.
- Merchant policies.

### 5.3 Hidden Actor State

The simulator should maintain latent state that drives events and delayed consequences:

- Customer satisfaction.
- Customer patience.
- Lifetime value.
- Fraud risk.
- Review probability.
- Chargeback probability.
- Repeat purchase probability.
- Shopper intent.
- Demand trends.
- Price sensitivity.
- Supplier reliability.
- Supplier lead time.
- Supplier defect rate.
- Carrier delay/loss/damage probability.
- Ad-channel response.
- Promo fatigue.
- Competitor pressure.
- Cash pressure.

### 5.4 Actor Simulators

#### Customers

Customers generate support tickets and react to agent messages/actions. Their latent state should change based on tone, timeliness, fairness, and operational outcome.

Customer types:

- Cooperative.
- Confused.
- Angry.
- VIP.
- Opportunistic.
- Adversarial.
- Repeat-refund risk.

#### Shoppers and Browsers

Shoppers generate traffic, abandoned carts, conversions, and demand signals. They react to price, inventory visibility, product copy, reviews, discounts, and ads.

#### Suppliers

Suppliers have cost, MOQ, lead time, fill rate, defect rate, cancellation risk, responsiveness, and payment terms.

Supplier events:

- Delayed shipment.
- Partial shipment.
- Invoice discrepancy.
- Defect batch.
- Price increase.
- Stockout.
- Faster but more expensive secondary source.

#### Logistics Providers

Carriers produce tracking events and exceptions.

Logistics events:

- Delayed package.
- Lost package.
- Damaged package.
- Customs hold.
- Address invalid.
- Delivery confirmation ambiguity.

#### Advertising Venues

Ad venues simulate spend, impressions, clicks, CPC, conversion rate, ROAS, attribution noise, audience fatigue, budget pacing, and promo interaction.

#### Merchant Policy Supervisor

The policy supervisor enforces refund rules, replacement rules, discount limits, margin floors, reorder approval thresholds, privacy constraints, VIP exceptions, and escalation requirements.

## 6. Agent Role and Authority

### 6.1 Agent Identity

The evaluated agent is a small-store owner, store manager, or merchant operator.

### 6.2 Objective

Maximize risk-adjusted store performance while obeying merchant policy.

### 6.3 Responsibilities

- Resolve support tickets.
- Handle refunds, returns, replacements, and cancellations.
- Investigate fulfillment exceptions.
- Adjust inventory.
- Create or update catalog data.
- Update tags and metafields.
- Create discounts.
- Respond to supplier issues.
- Manage purchase orders.
- Interpret analytics.
- React to ad performance.
- Escalate risky decisions.
- Produce operating reports.

### 6.4 Authority Levels

ShopWorld should evaluate agents across staged authority levels:

1. Read-only diagnosis.
2. Draft actions for merchant approval.
3. Supervised operator.
4. Bounded automation.
5. Capped write access.
6. Profit-share autonomous manager.

The near-term product should not sell unconstrained autonomy. It should sell evidence-based staged authority.

## 7. Shopify API Coverage

### 7.1 Coverage Principle

Prioritize high-frequency operational APIs over complete schema coverage.

The MVP should simulate Shopify Admin GraphQL behavior closely enough that agents learn real-world habits:

- Node IDs.
- Pagination.
- GraphQL cost and throttling.
- Scope errors.
- Mutation validation errors.
- Partial failures where applicable.
- Atomic updates for metafields.
- Order-access scope limitations.
- Bulk operation tradeoffs.

### 7.2 MVP Query Coverage

- `shop`
- `products`
- `productVariants`
- `orders`
- `order`
- `customers`
- `customer`
- `inventoryItems`
- `inventoryLevels`
- `locations`
- `fulfillmentOrders`
- `abandonedCheckouts`
- `discountNodes`
- `metafields`
- `metaobjects`
- `collections`

### 7.3 MVP Mutation Coverage

- `productCreate`
- `productUpdate`
- `productSet`
- Variant update mutations.
- `inventoryAdjustQuantities`
- `inventoryItemUpdate`
- `refundCreate`
- `orderUpdate`
- Fulfillment mutations.
- `customerUpdate`
- `tagsAdd`
- `tagsRemove`
- `metafieldsSet`
- `discountCodeBasicCreate`

### 7.4 Post-MVP Coverage

- Returns.
- Exchanges.
- Order editing.
- Bulk operations.
- Publications.
- Markets.
- Price lists.
- Subscriptions.
- Disputes.
- Shopify Flow-style admin actions.
- Webhook side effects.
- Real Shopify dev-store validation connector.

## 8. Scenario Taxonomy

### 8.1 Atomic API Tasks

Purpose: verify tool competence.

Examples:

- Update a product metafield.
- Adjust inventory at one location.
- Add a customer tag.
- Find orders affected by a SKU issue.
- Create a discount with expiry and constraints.

### 8.2 Support-Resolution Tasks

Purpose: test policy-grounded customer service plus correct store actions.

Examples:

- Late package complaint with carrier delay.
- Delivered-not-received complaint where replacement may beat chargeback risk.
- Wrong item shipped with scarce replacement inventory.
- Defective product linked to supplier batch issue.
- Price adjustment request after promotion launch.
- VIP urgent replacement before an event.
- Repeat-refund customer with abuse risk.
- Wrong address after fulfillment started.
- Misleading product description complaint.

### 8.3 Composite Operations Tasks

Purpose: test cross-domain investigation and action.

Examples:

- Three sizing complaints imply catalog variant metadata error.
- Supplier delay threatens open orders.
- Carrier exception affects high-LTV customers.
- Fraud wave affects fulfillment policy.
- Inventory discrepancy causes oversell risk.

### 8.4 Long-Horizon Management Episodes

Purpose: test business control over days or weeks.

Examples:

- Run the store for 7 simulated days.
- Run the store for 30 simulated days.
- Manage viral demand spike.
- Handle supplier outage under cash constraint.
- Balance ad spend, inventory, support backlog, and margin.

### 8.5 Stress Tests

- Flash sale traffic spike.
- Viral product.
- Supplier outage.
- Fraud wave.
- Carrier delay cluster.
- Ad underperformance.
- Review crisis.
- Cash crunch.
- Inventory aging.

### 8.6 Permission Tests

Evaluate agents under constrained scopes:

- Support-only.
- Fulfillment-only.
- Catalog-only.
- Inventory-only.
- Discount-only.
- Read-only analyst.
- Full-store operator.

### 8.7 Adversarial Tests

- Prompt-injection customer messages.
- Manipulative refund requests.
- Fake supplier emails.
- Ambiguous policy traps.
- Privacy-seeking attackers.
- Social engineering through support tickets.

## 9. Evaluation and Reward Design

### 9.1 Evaluation Principles

The evaluator should score outcomes, not just tool-call syntax.

A successful agent must:

- Complete the stated task.
- Preserve unrelated state.
- Follow policy.
- Avoid damaging margin, cash, inventory, customer trust, or compliance.
- Use APIs efficiently.
- Communicate appropriately.
- Maintain coherent strategy across time.

### 9.2 Core Metrics

#### Business Outcome

- Gross margin.
- Cash balance.
- Revenue.
- COGS.
- Refund leakage.
- Chargebacks.
- Sell-through.
- ROAS.
- Stockout rate.
- Inventory carrying cost.

#### Customer Outcome

- Complaint resolution.
- Response quality.
- Refund fairness.
- Repeat purchase probability.
- Review probability.
- NPS proxy.
- Escalation rate.

#### Operational Outcome

- Fulfillment SLA.
- Inventory accuracy.
- Supplier reliability.
- Backlog size.
- Ticket SLA.
- Incident recovery.

#### API Competence

- Correct GraphQL queries and mutations.
- Pagination handling.
- Node ID handling.
- Scope handling.
- Retry behavior.
- Cost awareness.
- Error recovery.

#### Safety and Compliance

- No unauthorized refunds.
- No margin-floor violations.
- No deceptive marketing.
- No privacy leakage.
- No unauthorized bulk changes.
- No policy override without escalation.

#### Coherence

- Avoids thrashing prices.
- Maintains strategy across days.
- Does not create contradictory customer promises.
- Does not oscillate inventory or campaign settings.

#### Explainability

- Produces auditable action log.
- Provides rationale for risky actions.
- Documents escalation decisions.

### 9.3 Evaluation Methods

#### State-Based Grading

Final database state is compared against valid expected outcomes.

Examples:

- Correct customer refunded.
- Correct order tagged.
- Correct inventory adjusted.
- Replacement created only when inventory and policy allow.
- Catalog metadata fixed without unrelated product damage.

#### Action-Based Grading

Used where sequence matters.

Examples:

- Do not send fulfillment confirmation before tracking exists.
- Do not refund before confirming identity when policy requires it.
- Do not promise replacement before checking inventory.

#### Collateral-Damage Checks

Compare initial and final state for unauthorized changes.

Examples:

- No unrelated product price changed.
- No bulk cancellation outside task scope.
- No customer emails sent to unrelated customers.
- No inventory changes outside affected SKUs.

#### Policy Compliance Checks

Verify actions against merchant policy and permission scope.

#### Trace Diagnostics

Classify failures by:

- Goal incomplete.
- Wrong tool arguments.
- Incorrect reasoning.
- Policy violation.
- Unauthorized write.
- API misuse.
- Customer communication failure.
- Environmental timeout.

### 9.4 Reward Vector

Use a vector reward rather than a single scalar at first:

- Task completion.
- Collateral damage penalty.
- Business impact.
- Customer impact.
- Operational impact.
- API cost.
- Policy compliance.
- Time/latency.
- Escalation quality.

A scalar can be derived later for RL training, but product reporting should preserve the vector.

## 10. Synthetic Data Strategy

### 10.1 MVP Store Archetype

Start with one store archetype to reduce complexity.

Recommended first archetype: apparel/accessories boutique.

Reasons:

- Common Shopify segment.
- Rich support issues: sizing, returns, shipping, variants, discounts.
- Easy to model catalog, seasonality, and promotions.
- Avoids regulated claims found in supplements or medical-adjacent products.

### 10.2 MVP Data Scale

Initial target:

- 1 store archetype.
- 50 products.
- 150 variants.
- 500 customers.
- 1,000 orders.
- 25 Shopify-like tools.
- 5 external simulators.
- 100 short tasks.
- 5 long episodes.
- 7-30 day episode length.
- 3 baseline agents.
- 12-15 reward metrics.

### 10.3 Public Dataset Inputs

Potential public inputs:

- Product catalogs.
- Ecommerce reviews.
- Complaint templates.
- Shipping delay distributions.
- Retail seasonality.
- Ad click/conversion benchmarks.
- Synthetic customer personas.

### 10.4 Store-Specific Customization

Later product loop:

1. Merchant grants read-only export permission.
2. ShopWorld imports product catalog, historical order velocity, inventory, customer tags, complaint history, supplier list, and existing automations.
3. Data generator fits category-level velocity, seasonal curves, complaint rates, supplier reliability, and margin norms.
4. Simulator creates private synthetic twin.
5. Agent is evaluated against merchant-specific scenarios.
6. Readiness report recommends permission scope and workflow authority.

No agent writes to the live store during evaluation.

## 11. Technical Architecture

### 11.1 High-Level Architecture

```text
ShopWorld
= deterministic runtime kernel
+ Shopify-like Admin GraphQL simulator
+ support inbox simulator
+ supplier/customer/logistics/ad/storefront actors
+ long-horizon business simulator
+ vector reward evaluator
+ scenario and counterfactual generator
+ rollout infrastructure
+ trace and replay engine
+ merchant-specific store clone importer
+ readiness reporting layer
```

### 11.2 Repository Structure

Recommended clean-room structure:

```text
shopworld/
  pyproject.toml
  README.md
  src/shopworld/
    environment.py
    task.py
    evaluator.py
    reward.py
    api_docs.py
    requester.py
    common/
    apps/
      lib/
      shopify_admin/
      support/
      suppliers/
      logistics/
      customers/
      ads/
      storefront/
    serve/
      http.py
      mcp.py
  generate/
    stores.py
    tasks.py
    scenarios.py
    counterfactuals.py
  experiments/
    agents/
    configs/
    run.py
    evaluate.py
  reports/
    readiness.py
  tests/
```

### 11.3 Components

#### Environment Runtime

Responsibilities:

- Reset world state.
- Load scenario initial state.
- Expose observations.
- Execute agent tool calls/messages.
- Advance simulated clock.
- Trigger actor events.
- Compute reward.
- Save traces.

#### Shopify Twin

Responsibilities:

- Store relational commerce state.
- Expose Shopify-like GraphQL API.
- Simulate cost, throttling, scopes, and pagination.
- Validate mutations.
- Produce realistic errors.

#### Support Inbox

Responsibilities:

- Manage tickets, messages, sentiment, promises, SLA timers, and attachments.
- Generate customer responses from hidden state.
- Track communication quality and policy compliance.

#### World Simulator

Responsibilities:

- Advance demand, inventory, fulfillment, supplier, ad, cash, and customer states.
- Generate exogenous events.
- Apply delayed consequences.

#### Task Engine

Responsibilities:

- Define scenario seed.
- Create initial state.
- Inject events.
- Define allowed authority.
- Define success and failure assertions.

#### Evaluator

Responsibilities:

- Score final state.
- Score trace.
- Detect collateral damage.
- Detect policy violations.
- Produce reward vector.
- Produce diagnostics.

#### Curriculum Engine

Responsibilities:

- Generate easy, medium, and hard variants.
- Mutate failure cases into counterfactuals.
- Support hill-climbing and RL training.

#### Readiness Report Generator

Responsibilities:

- Summarize performance by workflow.
- Summarize performance by permission scope.
- Estimate upside/downside.
- Identify high-risk permissions.
- Recommend staged deployment path.

## 12. Implementation Plan

### Phase 0: Product and Technical Decisions

Goal: lock the MVP scope.

Deliverables:

- Final MVP store archetype.
- Final Shopify API coverage list.
- Final scenario taxonomy.
- Reward vector v0.
- Authority-level model.
- Architecture decision record on clean-room implementation vs AppWorld fork.

Key decisions:

- Simulated Shopify first, live dev-store validation later.
- Single-agent first, multi-agent later.
- Admin API plus support inbox first, Storefront and ad APIs in staged order.
- Private merchant readiness first, public leaderboard later.

### Phase 1: Core Runtime Skeleton

Goal: create a runnable deterministic environment.

Build:

- `ShopWorldEnv.reset()`.
- `ShopWorldEnv.step(action)`.
- Scenario loader.
- Clock.
- SQLite or SQLModel database layer.
- State snapshot and restore.
- Trace logger.
- Basic evaluator interface.

Acceptance criteria:

- A seed creates repeatable state.
- Reset restores exactly.
- A simple tool action mutates state.
- Trace captures action and state diff.
- Evaluator can pass/fail a trivial task.

### Phase 2: Shopify Admin GraphQL MVP

Goal: expose realistic commerce action surface.

Build core models:

- Shop.
- Product.
- Variant.
- InventoryItem.
- InventoryLevel.
- Location.
- Customer.
- Order.
- FulfillmentOrder.
- Fulfillment.
- Refund.
- Discount.
- Metafield.
- Tag.

Build API behavior:

- MVP queries.
- MVP mutations.
- Node IDs.
- Pagination.
- Scopes.
- Validation errors.
- Cost/throttle simulation.

Acceptance criteria:

- Agent can inspect orders, customers, products, inventory, and fulfillments.
- Agent can perform bounded mutations.
- Invalid scopes and malformed mutations fail realistically.
- API docs are available to agent.

### Phase 3: Support Inbox and Customer Simulator

Goal: make customer service a first-class loop.

Build:

- Ticket model.
- Message model.
- SLA timer.
- Sentiment state.
- Customer latent variables.
- Customer response generator.
- Policy-aware grading for replies.

Acceptance criteria:

- Customer complaint triggers from hidden state.
- Agent can message customer and perform Shopify action.
- Customer responds deterministically from seed and state.
- Evaluator scores resolution, tone, policy, and business outcome.

### Phase 4: External Actor Simulators

Goal: create coupled operational dynamics.

Build:

- Supplier simulator.
- Logistics simulator.
- Shopper/demand simulator.
- Advertising simulator.
- Merchant policy supervisor.

Acceptance criteria:

- Delays, stockouts, defects, traffic changes, and ad changes create downstream events.
- Agent actions affect future simulator state.
- Long-horizon episodes produce non-trivial tradeoffs.

### Phase 5: Scenario Library MVP

Goal: create enough tasks to benchmark agents.

Build:

- 20 atomic API tasks.
- 30 support-resolution tasks.
- 25 composite ops tasks.
- 15 stress/permission/adversarial tasks.
- 5 long-horizon episodes.
- Task metadata: difficulty, domain, required scopes, hidden state, success checks, collateral-damage checks.

Acceptance criteria:

- 100 short tasks are deterministic.
- 5 long episodes run end-to-end.
- Each task has state-based grading.
- Challenge tasks support pass^k evaluation.

### Phase 6: Reward, Diagnostics, and Reports

Goal: make evaluation product-grade.

Build:

- Reward vector.
- Collateral-damage diff engine.
- Policy violation detector.
- Fault classifier.
- Per-scope scorecards.
- Merchant readiness report.

Readiness report fields:

- Store clone readiness score.
- Expected profit uplift.
- Worst-case drawdown.
- Policy violation rate.
- Refund leakage risk.
- Inventory risk.
- Human escalation rate.
- Recommended write-access scope.
- Workflow-by-workflow readiness.

Acceptance criteria:

- Reports are understandable to merchants.
- Reports cite representative failures.
- Reports recommend staged authority.
- Reports separate model failures from environment/timeouts.

### Phase 7: Baseline Agents and Training Loop

Goal: prove evaluation differentiates agents and supports improvement.

Build baseline agents:

- Simple function-calling agent.
- ReAct/tool agent.
- Policy-constrained agent with explicit escalation.

Build training loop:

- Scenario replay.
- Counterfactual generation.
- Difficulty curriculum.
- Failure-driven prompt/policy hill-climbing.
- Optional Gym-compatible wrapper.

Acceptance criteria:

- Baselines produce different score profiles.
- Counterfactuals expose consistent weaknesses.
- Agent iteration improves on targeted failure clusters.

### Phase 8: Merchant-Specific Twin

Goal: make ShopWorld commercially differentiated.

Build:

- Read-only Shopify export connector.
- Store-prior fitting pipeline.
- Synthetic twin generation.
- Privacy and PII stripping.
- Merchant-specific scenario generator.

Acceptance criteria:

- Merchant can import store priors without write access.
- Synthetic twin resembles store category, SKU, order, and complaint patterns.
- Agent readiness report reflects merchant-specific risks.

## 13. MVP Cut Line

### Must Have

- Deterministic environment reset/step loop.
- Simulated Shopify Admin GraphQL core objects.
- Support inbox.
- Customer simulator.
- Supplier simulator.
- Logistics simulator.
- Basic demand simulator.
- Basic ad simulator.
- Policy supervisor.
- 25 Shopify-like tools.
- 100 short tasks.
- 5 long episodes.
- Reward vector.
- Collateral-damage checks.
- Trace/replay.
- Baseline agents.
- Readiness report.

### Should Have

- GraphQL cost/throttle simulation.
- Scope bundles.
- Counterfactual generator.
- pass^k scoring.
- Fault classifier.
- Gym wrapper.

### Defer

- Public leaderboard.
- Real Shopify dev-store validation.
- Multi-agent teams.
- Full Storefront API.
- Real Meta/Google sandbox integrations.
- Complex markets/subscriptions/B2B.
- Profit-share deployment product.

## 14. Counterfactual Generator

Counterfactuals are a key training asset.

Examples:

- Same demand, lower cash.
- Same supplier, longer lead time.
- Same complaint, VIP customer.
- Same orders, higher fraud.
- Same inventory, ad spike.
- Same product, worse reviews.
- Same logistics, lost package.
- Same promotion, margin compression.
- Same campaign, creative fatigue.

Use counterfactuals to create scenario families and identify whether the agent learned robust operating principles or brittle scripts.

## 15. Merchant Readiness Product

### 15.1 Report Structure

Recommended sections:

1. Executive readiness score.
2. Workflow readiness by domain.
3. Permission-scope recommendation.
4. Business impact estimate.
5. Worst-case failure examples.
6. Policy violation analysis.
7. Customer trust risk.
8. Inventory and fulfillment risk.
9. API competence score.
10. Suggested staged deployment plan.

### 15.2 Deployment Recommendation Model

Map scores to authority:

- Read-only diagnosis: safe when query and reasoning are reliable but write actions are risky.
- Draft-only: safe when recommendations are strong but mutations need review.
- Supervised operator: safe when low-risk workflows are reliable.
- Bounded automation: safe for narrow workflows with low collateral damage.
- Capped write access: safe when high-volume tasks pass under stress.
- Autonomous manager: only after long-horizon operating episodes are consistently strong.

## 16. Risks and Mitigations

### 16.1 Simulator Realism Risk

Risk: agents overfit synthetic dynamics.

Mitigation:

- Use public data distributions.
- Add merchant-specific priors.
- Validate later against Shopify dev stores.
- Maintain scenario diversity and counterfactuals.

### 16.2 Scope Creep Risk

Risk: trying to simulate all of Shopify.

Mitigation:

- Prioritize high-traffic operational workflows.
- Start with one store archetype.
- Build API depth before breadth.

### 16.3 Evaluation Credibility Risk

Risk: merchants do not trust synthetic readiness scores.

Mitigation:

- Show traces and concrete failure examples.
- Tie scores to workflows and permissions.
- Allow custom merchant scenarios.
- Include conservative staged-authority recommendations.

### 16.4 Safety Risk

Risk: product messaging implies autonomous control too early.

Mitigation:

- Position as evaluation and staged deployment.
- Default to read-only/draft-only recommendations.
- Treat live write access as later-stage product.

### 16.5 Technical Fidelity Risk

Risk: Shopify GraphQL behavior diverges from real API.

Mitigation:

- Version the simulated schema.
- Include common GraphQL constraints.
- Add test fixtures from Shopify docs.
- Validate against dev stores post-MVP.

## 17. Immediate Next Steps

1. Decide first store archetype.
2. Finalize MVP API object/mutation coverage.
3. Define first 20 scenarios with state, hidden state, tools, and assertions.
4. Create clean `shopworld` runtime skeleton.
5. Implement SQLite/SQLModel commerce schema.
6. Implement GraphQL query/mutation dispatcher.
7. Build first support-ticket scenario end-to-end.
8. Add collateral-damage diff checks.
9. Build first baseline agent.
10. Generate first readiness-report prototype.

## 18. Decision Log

Recommended initial decisions:

- Simulated Shopify first; real Shopify connector later.
- Merchant-readiness product first; public benchmark later.
- Single-agent first; multi-agent later.
- Apparel/accessories boutique first.
- Customer support + fulfillment + inventory as MVP core.
- Admin GraphQL + support inbox first; Storefront and ad integrations progressively expanded.
- Vector reward first; scalar RL reward later.

## 19. Definition of Done for MVP

The MVP is complete when:

- A deterministic simulated store can be generated and reset.
- An agent can interact through Shopify-like tools and support messages.
- At least 100 short scenarios and 5 long episodes run end-to-end.
- Evaluation catches task failure, policy failure, API misuse, and collateral damage.
- At least 3 baseline agents produce meaningfully different reports.
- A merchant-facing readiness report recommends workflow and permission scope.
- The system supports failure replay and counterfactual scenario generation.
