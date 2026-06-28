# Architecture

Seven subsystems, each independently testable. Data flows left to right:
taxonomy → scenarios → (persona + NLG) → adapter/dialogue → oracle → reporting.

## 1. Engine (determinism spine)

`engine/rng.py` — `DeterministicRNG` wraps a single `numpy.random.Generator(PCG64)`
stream. The only sanctioned randomness source. Sub-streams are derived by
hashing a label into a child seed (`derive_seed`, BLAKE2b), so subsystems hold
independent reproducible streams. `weighted_choice` samples by inverse-CDF over
ordered inputs for stability.

`engine/hashing.py` — `canonical_json` + `content_hash` (BLAKE2b-128) give every
frozen artifact a stable content address. `Manifest` pins a whole run by hashing
all inputs plus the engine version into one root hash.

`engine/types.py` — frozen dataclasses shared everywhere: `Lifecycle`,
`IntentLayer`, `Vertical`, `QueryFamily`, `Persona`, `Goal`, `Factsheet`,
`Scenario`.

## 2. Taxonomy & scenario graph

`taxonomy/registry.py` — all 52 macro families as data: lifecycle stage, intent
layer, single-shot/multistep classification, typical info slots, vertical
overlays. `HARD_CORE_MULTISTEP` names the 12 families that presuppose journey
state.

`taxonomy/graph.py` — `JourneyGraph`, an in-memory weighted property graph.
Edges: `PRECEDES` (lifecycle order), `ESCALATES_TO` (happy path → exception),
`REQUIRES` (state presupposition), `COMPLEMENTS`/`SUBSTITUTES`. A seeded weighted
walk over this graph composes exploratory multi-family journeys. **The graph is
authoring-only** — compiled scenarios are frozen JSON; the runtime never touches
it.

`taxonomy/falkor_store.py` — `FalkorJourneyStore`, a FalkorDB backend for the
graph. `sync` mirrors the canonical in-memory graph into FalkorDB (deterministic,
sorted writes); `load` reconstructs it; `journeys_into` computes prerequisite
chains with Cypher. Lazy-imported, off the runtime path, degrades gracefully
with no server.

`taxonomy/scenario_compiler.py` — compiles families into immutable,
content-addressed `Scenario` artifacts. Single-shot families get a one-goal
builder; the 12 hard-core families get bespoke multi-goal builders whose
preconditions force real multi-turn journeys; `compile_graph_journey` generates
precondition-linked stacks by walking the journey graph. `compile_full_battery`
expands vertical overlays (one scenario per family × applicable overlay).
`scenario_id` is the content hash.

## 3. Persona & behaviour engine

`persona/library.py` — 8 fixed, named archetypes (bargain hunter, anxious
gifter, spec maximalist, …) as trait vectors in [0, 1]. Fixed so the battery
stays comparable.

`persona/behavior.py` — two deterministic layers: a journey-level Markov chain
over lifecycle stages (transition weights modulated by persona traits), and
within-state Bayesian-style decision models (logistic CPTs over traits) for
choices like abandon-vs-continue or accept-vs-decline-substitution.

## 4. Controllable NLG (no LLM at runtime)

`nlg/lexicon.py` — small controlled vocabularies for slot filling.
`nlg/paraphrase_bank.py` — frozen per-family templates across registers
(terse/neutral/polite). In production this bank is LLM-generated offline and
human-checked, then frozen; at runtime the realiser only *selects*.
`nlg/realizer.py` — picks a register from persona traits (seeded), selects a
template (seeded), fills slots, injects seeded typo/abbreviation noise for
low-fluency personas. Same inputs → byte-identical utterance.

## 5. Harness / adapters

`adapters/base.py` — the `MerchantAdapter` protocol and `MerchantTurn`
observation.

`adapters/turn_classifier.py` — deterministic classification of merchant turns
into dialogue moves using structural signals + frozen keyword banks + the active
goal's satisfaction signals. **Fail-closed**: near-boundary responses become
`AMBIGUOUS`, not a generous `ANSWERED_GOAL`. (Production swaps the keyword
overlap for a pinned embedding model with a cached, hashed classification; the
interface is identical.)

`adapters/dialogue_policy.py` — **the multistep core.** A state machine over the
goal stack. After each merchant turn it classifies, then transitions: provide a
factsheet slot, decline an impossible ask, confirm/decline an offered action,
rephrase (bounded), escalate, accept a handoff, or abandon — every choice seeded
and persona-parameterised. Goal preconditions are checked against accumulated
journey state, which is what makes multistep structural rather than optional.
Guards: global + per-goal turn budgets and loop detection guarantee
termination.

`adapters/mock_merchant.py` — deterministic scriptable merchants (Good,
Clueless, Overeager, Refusing) for tests/demos.
`adapters/agent_adapter.py` — `HTTPAgentAdapter` (httpx, configurable contract)
and an `MCPAgentAdapter` shell.
`adapters/web_adapter.py` — `PlaywrightWebAdapter` + `PageModel` (Shopify preset).

## 6. Oracle & scoring

`oracle/rubric.py` — versioned dimension weights.
`oracle/scorer.py` — pure function from transcript → `ScenarioScore` across
task_success / efficiency / correctness / disclosure / recovery, plus layer
roll-up and headline. Penalises impossible asks, unnecessary clarifies,
precondition violations, and goals satisfied without gathering required info.

## 7. Orchestration & reporting

`orchestrator/runner.py` — runs scenarios × personas × seeds × K-repeats. The
shopper is deterministic, so cross-repeat variance is merchant-attributable and
reported as a stdev. Emits a content-addressed run manifest.
`reporting/scorecard.py` — human-readable scorecards and a generation diff that
attributes per-scenario regressions/improvements and refuses to compare runs
built on different batteries.

## Production path (out of scope here)

The reference engine runs standalone. The journey graph already has a FalkorDB
authoring backend (`falkor_store.py`). A full production deployment would add:
offline LLM tooling to generate the paraphrase
bank and a frozen, cached free-text judge (tier-2/3 scoring); Temporal for
durable battery runs; FastAPI + Postgres + object store for the service and
transcript storage; and a ruff plugin + import-linter contract enforcing the
determinism rules in CI.
