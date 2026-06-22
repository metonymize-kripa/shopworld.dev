# ShopWorld Completion Recommendations

_Date: 2026-06-22. Reviewed against `platform-rnd/README.md` (the active contract) and the `shopworld-platform/` codebase at commit `fe4a357`._

**Problem.** The environment half is real and tested. The benchmark half does not exist. `platform-rnd/README.md` defines a comparative benchmark: run milli.run and an LLM agent against identical scenarios through one tool surface, then report who fails where. Today there are zero agents, no runner, and no comparative report. The repo can simulate a store and score a trace, but it cannot run the experiment the document is named after.

**State of the build.** 151 tests pass on Python 3.10. The Merchant API Surface exposes the full 25-tool contract (`api_surface/merchant.py`, 763 LOC). Five state-dependent workflow families exist as Python factories (`tasks/wismo.py`, `cancellation.py`, `address_change.py`, `refund.py`, `return_item.py`). The rich `Evaluator` is wired into `env.evaluate()` and reads real serialized state, not `{}`. The duplicate GraphQL layer is deprecated, not dead-imported. This is meaningfully past the 2026-06-18 review — the P1 "vertical slice" is done.

## Gap map against §12 Execution Sequence

| Step | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1–4 | Core loop, schema, API surface, support inbox | Done | `environment.py` (827), `models.py` (656), `api_surface/merchant.py` (763) |
| 5–6 | Bitext support/retail scenario generators | **Missing** | No `bitext_*` module, no Bitext data, no grep hit in `src` |
| 7 | Five workflow families | Done | 5 factories in `tasks/` |
| 8 | Evaluator (final-state + trace) | Done | `evaluator.py` (457), wired into `env.evaluate()` |
| 9–10 | milli.run NLU + workflow router + guards | **Missing** | No `milli_run/` package anywhere |
| 11 | LLM tool-use agent | **Missing** | No `llm_agent/` package anywhere |
| 12 | 30-scenario MVP benchmark run | **Missing** | `experiments/` dirs empty; no `run_benchmark.py` |
| 13 | Failure-taxonomy report | **Missing** | No report generator; nothing to compare |
| 14–15 | Scenario expansion, long-horizon episodes | Not started | — |

## Definition-of-Done gaps (§13)

- **NLU benchmark, failure report, agent-interface equality** — all blocked on the two missing agents. These three are the core deliverables and none can be produced yet.
- **Determinism** — partially broken. `reset()` and task generation call global `random.seed()` (`environment.py:154`, `task.py:56`). Any unrelated code touching global random breaks replay. Carried over unfixed from the 2026-06-18 review (issue C2).
- **Trace replay** — traces are recorded (`TraceStep`), but there is no replay module. README §11 specifies `traces/replay.py`; it does not exist. "Any failed episode can be replayed deterministically" is unproven.

## Recommendations, prioritized

The breadth is already built. Stop adding environment surface area. Build the experiment.

**P0 — Make the benchmark runnable end to end.** Without this nothing else in the README is demonstrable.

- Build the neutral runner: `experiments/run_benchmark.py` implementing the §7 ten-step loop (load scenario → reset env → reset agent → observe → act → execute → repeat → evaluate → save trace → compare). Add `experiments/configs/mvp_30.yaml`.
- Define one `Agent` protocol — `reset(observation)` and `act(observation) -> Action` — so the runner stays agent-blind and §13 "interface equality" holds by construction.
- Ship a trivial baseline agent first (scripted/random) to prove the loop runs before either real agent exists.

**P1 — Build the two agents under test.** This is the product. Per §11:

- `milli_run/`: FastText/SVM intent classifier, entity extractor, confidence router, workflow state machines for the 5 families, transaction guards, commit/rollback, audit log. It may touch ShopWorld **only** through the Merchant API Surface (§7).
- `llm_agent/`: prompt policy, ReAct/tool-use loop, planner, escalation logic, same tool surface.
- Gate: an integration test where milli.run and the LLM agent run the *same* scenario and the runner records both traces.

**P2 — Close determinism and replay.** Cheap, unblocks the §13 determinism + replay rows.

- Thread one injected `random.Random` through `env`, `task`, and simulators. Delete global `random.seed()` calls.
- Add `traces/replay.py` plus a test asserting identical final state from same seed + action log.

**P3 — Bitext scenario generators and scenario count.** §10 wants 500 support + 500 retail utterances and 30 grounded scenarios with 5 hidden-state variants per workflow. Today: 5 hand-coded factories (~13 scenario variants), no Bitext.

- Build `scenarios/bitext_support_importer.py` and `bitext_retail_importer.py`. Enforce the §6 leakage rule: NLU-training splits must not reuse held-out test language. Track every seed utterance by split and provenance.
- Expand factories to hit 30 verified scenarios.

**P4 — Comparative failure-taxonomy report.** The payoff artifact (§9). Once both agents produce traces, generate the report that bins failures into the §9 milli.run vs LLM taxonomies and emits the reward vector + readiness output.

## Scope call needed from you

**The shopper-facing benchmark (§5) is entirely absent.** It is ~40% of the README — a separate Postgres/Solr-style store, 9 anti-oracle tools (`search_products`, `resolve_alias`, `check_compatibility`, …), a vanilla-search baseline, and a Baymard/Bitext/ESCI query generator. An earlier `amazon_simulator` attempt was deleted (only orphan `.pyc` files remain). README §10 scopes the *MVP* to merchant workflows (WISMO etc.), so §5 reads as post-MVP. Recommendation: explicitly defer §5 until the merchant benchmark produces its first comparative report, and mark it deferred in the README so it stops reading as in-scope-but-broken.

## Hygiene (do alongside, not instead)

- `env._compute_business_metrics()` returns hardcoded zeros (`environment.py:480`). The Evaluator recomputes from the trace, so the env method is dead and misleading — delete it or make it real.
- `demand_sim`, `ad_sim`, `supplier_sim`, `policy_supervisor` are declared then set to `None` in `_init_simulators` (`environment.py:320`). §7 lists demand and ads simulators as owned components. Either wire supplier_sim (it's already built, 138 LOC) or document these as deferred.
- Old `graphql.py` (549 LOC) is deprecated but still in the tree. Delete once nothing references it.

**TL;DR.** Environment: done and tested. Benchmark: not started. Build the runner + an agent protocol (P0), then milli.run and the LLM agent (P1) — that is the entire point of ShopWorld and currently the only thing standing between this repo and an MVP. Fix determinism/replay (P2) in passing, then Bitext scenarios (P3) and the comparative report (P4). Defer the §5 shopper benchmark explicitly.
