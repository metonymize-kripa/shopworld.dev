# ShopWorld Comparative Benchmark Report

_Episodes: 270 across 3 agents._

## Aggregate results

| Agent | Episodes | Success | Success rate | Avg score | Avg API cost | Scope viol. | Collateral | Refund leakage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 90 | 54 | 60% | 56.0 | 20.0 | 0 | 0 | 0.0 |
| milli_run | 90 | 90 | 100% | 80.0 | 31.7 | 0 | 0 | 0.0 |
| llm_agent | 90 | 75 | 83% | 70.0 | 25.3 | 0 | 0 | 0.0 |

## Failure taxonomy (README §9)

**baseline**

- `missing_workflow`: 36

**milli_run**: no failures.

**llm_agent**

- `policy_drift`: 15

## Example failures

**baseline**

- cancellation-unfulfilled-42 (seed 1): `missing_workflow` — Baseline performs no state-changing action
- cancellation-unfulfilled-42 (seed 2): `missing_workflow` — Baseline performs no state-changing action
- cancellation-unfulfilled-42 (seed 3): `missing_workflow` — Baseline performs no state-changing action
- cancellation-unfulfilled-43 (seed 1): `missing_workflow` — Baseline performs no state-changing action
- cancellation-unfulfilled-43 (seed 2): `missing_workflow` — Baseline performs no state-changing action

**llm_agent**

- escalation-legal_threat-42 (seed 1): `policy_drift` — Failed to escalate abuse / refunded without policy check
- escalation-legal_threat-42 (seed 2): `policy_drift` — Failed to escalate abuse / refunded without policy check
- escalation-legal_threat-42 (seed 3): `policy_drift` — Failed to escalate abuse / refunded without policy check
- escalation-chargeback_threat-42 (seed 1): `policy_drift` — Failed to escalate abuse / refunded without policy check
- escalation-chargeback_threat-42 (seed 2): `policy_drift` — Failed to escalate abuse / refunded without policy check

## NLU benchmark (milli.run)

- Held-out intent accuracy: 94% on 85 utterances (trained on built-in + Bitext nlu_train split; evaluated on disjoint held-out split per the leakage rule).
- Entity extraction sanity (amount/email/order-ref): pass.


## Interpretation

milli.run's advantage concentrates in policy/escalation correctness and auditability (every decision is logged with its cause and a rollback plan). The LLM agent matches it on language-flexible workflows but lacks hard guards and an audit trail, so its failures cluster in policy drift on abuse/fraud cases. The baseline floor shows how much of the score comes from taking the correct state-dependent write action rather than just replying.
