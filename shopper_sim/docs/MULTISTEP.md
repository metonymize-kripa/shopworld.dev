# Multistep: how it's secured

Single-shot graders test "type a query, read the answer." That misses the
families where merchant agents actually break: the ones that presuppose journey
state. You cannot test "track my order" with one query — there has to *be* an
order, and the agent has to establish *which* one before it can answer. This
doc explains the mechanism that makes those journeys structural.

## The 12 hard-core multistep families

`order_editing`, `order_failure`, `live_fulfillment`, `tracking`,
`delivery_exceptions`, `return_initiation`, `exchanges_replacements`, `refunds`,
`warranty_repair`, `subscriptions`, `support_escalation`, `b2b_pro`.

Each presupposes state that cannot exist in a single query. The simulator
encodes that with four cooperating pieces.

## 1. Goal stack with preconditions

A scenario compiles to an ordered stack of `Goal`s. Each goal has:

- `preconditions` — journey-state keys that must hold before it can be pursued.
- `establishes` — keys it produces once satisfied.
- `info_slots` — slots the shopper is willing to provide if asked.
- `satisfaction_signals` — what the merchant must say/do to close it.

Example — `tracking`:

```
goal locate_order:  pre=(order_exists,)   establishes=(order_located,)
goal track_order:   pre=(order_located,)  establishes=(status_known,)
```

`track_order` cannot run until `order_located` is true, and only `locate_order`
can set that. The dependency is checked at runtime
(`DialoguePolicy._preconditions_met`). A merchant that "answers" tracking without
first establishing the order leaves `order_located` false, so the second goal is
recorded `precondition_unmet` and scored as a failure. There is no single-query
path that satisfies the stack. (`test_goal_precondition_chain_is_satisfiable`
checks every hard-core scenario's chain is internally consistent;
`test_precondition_blocks_dependent_goal_when_prereq_fails` checks enforcement.)

## 2. Ground-truth factsheet

Each scenario carries an immutable `Factsheet` of what the shopper knows. The
dialogue policy answers a merchant's clarifying questions **only** from it:

- Slot on the factsheet → the shopper provides exactly that value
  (`test_shopper_answers_only_from_factsheet`).
- Slot absent → the shopper truthfully declines ("I don't have that"), and the
  turn is scored as an **impossible ask** — a merchant error
  (`test_impossible_ask_is_declined_truthfully`).
- The shopper **never volunteers** a slot it wasn't asked for. This is what
  measures whether the agent *knows what to ask*.

## 3. Deterministic dialogue policy

A state machine (no LLM) drives each goal:

```
OPENING → AWAIT_MERCHANT → {classify} →
    ANSWERED_GOAL      → pop goal, establish state
    ASKED_CLARIFY(s)   → provide s from factsheet, or decline if absent
    ASKED_VERIFY       → provide identity proof if known
    OFFERED_ACTION     → confirm/decline per persona risk-aversion (seeded)
    STALLED/AMBIGUOUS  → rephrase (bounded) → escalate or abandon
    REFUSED/HANDED_OFF → record terminal outcome
```

Every branch that involves a choice is sampled from the seeded RNG,
parameterised by persona traits, so the shopper is reproducible even against a
stochastic merchant.

## 4. Guards

Global turn budget (24), per-goal budget (6), rephrase budget (2), and loop
detection (same shopper utterance + same merchant move twice → break). These
guarantee every dialogue terminates deterministically
(`test_loop_detection_terminates`, `test_turn_budget_is_respected`).

## Same policy, both adapters

The policy is transport-agnostic. For the agent adapter, a "merchant turn" is a
chat message. For the web adapter, it's a page state and the shopper's
"utterance" is a DOM action. A multistep return on a form-driven Shopify store
runs through the identical state machine — only the adapter binding differs.

## What a skipped step costs

A merchant that resolves a multistep goal *without* gathering the info it needs
(the `OvereagerMerchant`) is flagged `skipped_required_info` and penalised in
the correctness dimension (`test_overeager_merchant_penalised_on_multistep`).
This is why an over-eager merchant scores below a careful one specifically on
the exception layer, even though both "complete" the task.
