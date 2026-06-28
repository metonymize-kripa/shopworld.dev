# Shopper Simulator

A deterministic, reproducible behavioural-simulation engine that grades
e-commerce experiences — single-shot web storefronts **and** multi-step
merchant agents — against a frozen battery of shopper-intent tests. Point it at
a merchant, get a score, hill-climb across generations of your AI.

The core bet: make the **shopper** fully deterministic and push all variability
into the thing under test. Same `(scenario, persona, seed)` always produces the
same shopper behaviour, byte-for-byte, across processes. That gives you a stable
ruler — you can compare gen-N against gen-N+1 and trust the delta.

## What it covers

- **All 52 macro query families** from the source taxonomy (discovery →
  evaluation → cart → checkout → fulfillment → post-purchase → returns →
  account), rolled up to seven intent layers for scoring.
- **39 multistep / escalating families**, of which **12 are "hard core"** —
  they presuppose journey state (an order exists, an item was delivered, a
  subscription is active) and *cannot* be tested by a single query. These are
  where merchant agents fail and where single-shot graders are blind.

## Why multistep is actually secured

The hard part of grading a merchant agent is holding context across turns. The
simulator forces that structurally:

- **Goal stack.** Each scenario compiles to an ordered stack of goals. A goal
  carries a *precondition* (journey state it presupposes) and *establishes*
  (state it produces). `track_order` requires `order_located`, which an earlier
  `locate_order` goal establishes. You cannot satisfy the second goal without
  completing the first — there is no single-query shortcut.
- **Ground-truth factsheet.** Each scenario has an immutable record of what the
  shopper knows (order ids, addresses, payment on file). The shopper answers a
  merchant's clarifying questions **only** from the factsheet, and **never
  volunteers** an unasked slot. Ask for something the shopper wasn't given and
  you get a truthful "I don't have that" — scored as a merchant error.
- **Deterministic dialogue policy.** A state machine (no LLM) decides the
  shopper's next move after every merchant turn: provide a slot, decline an
  impossible ask, confirm or decline an offered action, rephrase, escalate, or
  abandon. Every *choice* is seeded and persona-parameterised, so the shopper is
  reproducible even when the merchant is stochastic.
- **Fail-closed turn classifier.** Merchant responses near a classification
  boundary are marked `AMBIGUOUS` (scored as merchant-unclear) rather than
  optimistically counted as a goal answer, so a vague merchant isn't flattered.

The same goal stack drives both adapters: for the agent adapter, "merchant
turns" are chat messages; for the web adapter, they're page states and the
shopper's "utterances" are DOM actions. A multistep return on a Shopify
storefront runs through the identical state machine.

## Install & Run

Requires Python 3.12+.

We standardise on Astral `uv` for managing dependencies and execution. There is no need to manually activate a virtualenv or run `pip install` — standard python/pytest commands should be run using `uv run`:

```bash
# Run the test suite
uv run python -m pytest

# Run formatting checks
uv run ruff check
```

If you need to install specific extras (e.g. for agents, web storefronts, or graph sync), you can run:

```bash
uv sync --all-extras
```

The runtime engine depends only on **numpy**. `httpx`, Playwright, the FalkorDB
client, and the graph server are optional and imported lazily — the offline
engine and the whole test suite run with numpy alone.

## Quick start (CLI)

```bash
# Print the full 52-family coverage matrix (S = single-shot, M = multistep,
# * = hard-core multistep).
uv run shopper-sim coverage

# Run the battery against a built-in mock merchant.
uv run shopper-sim run --merchant good --k 5
uv run shopper-sim run --merchant good --persona-mode cross   # every persona
uv run shopper-sim run --merchant good --no-overlays          # compact 52-scenario
uv run shopper-sim run --merchant good --dump-transcripts run.json

# Show a generation diff (a weak merchant vs a good one on the same battery).
uv run shopper-sim demo-diff

# Sync the journey graph into FalkorDB for authoring/visualisation.
uv run shopper-sim graph-sync --show-into refunds

# Run examples directly.
uv run python examples/run_full_battery.py
uv run python examples/generation_diff.py
uv run python examples/show_multistep_dialogue.py
```

Built-in mock merchants (`good`, `clueless`, `overeager`) exist so you can see
score separation immediately and study the adapter contract. Typical headline
separation: good ≈ 92, overeager ≈ 88 (loses on hard-core multistep where it
skips info-gathering), clueless ≈ 33.

## Quick start (Python)

```python
from shopper_sim import (
    compile_full_battery, run_battery, all_personas,
    GoodMerchant, format_scorecard,
)

scenarios = compile_full_battery()           # 59 scenarios (family x overlay)
run = run_battery(
    scenarios, all_personas(),
    adapter_factory=lambda s: GoodMerchant(s),
    k_repeats=5, battery_version="my-run-1",
    persona_mode="cross",                     # every scenario x every persona
    capture_transcripts=True,                 # retain replayable transcripts
)
print(format_scorecard(run))
```

`persona_mode` is `"recommended"` (one persona per scenario; compact) or
`"cross"` (the full cross-product — 59 scenarios × 8 personas = 472 cells). The
manifest records which mode ran, so a recommended run and a cross run hash
differently and aren't silently compared.

`compile_full_battery()` expands vertical overlays by default: a family with
multiple overlays (e.g. `warranty_repair` under electronics *and* home) yields
one scenario per overlay. Pass `expand_overlays=False` for a compact 52-scenario
smoke battery.

### Replay

With `capture_transcripts=True`, every run keeps the full per-turn record — each
shopper utterance, merchant response, classification, outcome, and goal result —
serialisable via `transcript.to_dict()`. From the CLI:

```bash
uv run shopper-sim run --merchant good --dump-transcripts run.json
```

`run.json` contains every cell's transcripts; because the shopper is
deterministic, re-running the same `(scenario, persona, seed)` reproduces them
byte-for-byte.

## Grading a real merchant

Implement the `MerchantAdapter` protocol (three methods: `open_session`,
`send`, `close_session`) or use the bundled `HTTPAgentAdapter`:

```python
from shopper_sim.adapters.agent_adapter import HTTPAgentAdapter
from shopper_sim import run_battery, all_personas, compile_full_battery

run = run_battery(
    compile_full_battery(), all_personas(),
    adapter_factory=lambda s: HTTPAgentAdapter("https://your-store.example/chat"),
    k_repeats=3, battery_version="prod-gen-7",
)
```

The default HTTP contract sends `{"message", "session_id", "history"}` and reads
`{"reply"}`. If your API differs, pass `request_builder` / `response_parser`
callables — see `examples/grade_real_agent.py`. For web storefronts, use
`PlaywrightWebAdapter` with a `PageModel` (a Shopify preset ships by default).

## Scoring

Each scenario is scored on five dimensions, weighted and rolled up to a headline
in [0, 100] plus a per-intent-layer breakdown:

| Dimension      | Weight | Measures |
|----------------|--------|----------|
| task_success   | 0.40   | fraction of the goal stack completed |
| correctness    | 0.25   | right info asked for; impossible asks, unnecessary clarifies, precondition violations, and skipped-required-info penalised |
| efficiency     | 0.15   | turns relative to optimal |
| disclosure     | 0.10   | fees/policy/trust surfaced before resolution |
| recovery       | 0.10   | graceful handling of stalls, ambiguity, refusals |

Weights are public and versioned (`RUBRIC_VERSION`) so the ruler is auditable.

Each scenario runs **K times** (different shopper phrasings, same goal
structure). Because the shopper is deterministic, any score variance across the
K repeats is attributable to the merchant — reported as a standard deviation
next to each scenario. A flagged `(inconsistent)` scenario means the merchant
itself is non-deterministic there.

## Hill-climbing across generations

Runs on the *same* `battery_version` share a content-addressed root hash. Diff
them to attribute regressions and improvements per scenario:

```python
from shopper_sim import diff_runs, format_diff
print(format_diff(diff_runs(gen_n, gen_n_plus_1)))
```

The diff refuses to mislead you: if the two runs used different batteries (a
different ruler), it says so and marks the scores incomparable.

## The journey graph (FalkorDB)

Scenarios are composed over a weighted property graph of the 52 families, with
edges for lifecycle order (`PRECEDES`), happy-path-to-exception (`ESCALATES_TO`),
and state presupposition (`REQUIRES`). The graph drives two things:

- **Graph-generated scenarios.** `compile_graph_journey(start_family, seed)`
  walks the graph (seeded, weighted) and chains each visited family into a
  precondition-linked goal stack — exploratory multistep journeys distinct from
  the curated hard-core templates.
- **Authoring in FalkorDB.** The canonical in-memory graph syncs to FalkorDB so
  you can query/extend it with Cypher:

  ```python
  from shopper_sim.taxonomy.falkor_store import FalkorJourneyStore
  store = FalkorJourneyStore()
  store.sync()                          # mirror the canonical graph into FalkorDB
  store.journeys_into("refunds")        # prerequisite chains, computed in-graph
  graph = store.load()                  # reconstruct the in-memory graph
  ```

  FalkorDB is **authoring-only** — it never sits on the runtime scoring path,
  matching the determinism contract. Start a server with
  `docker run -p 6379:6379 -it --rm falkordb/falkordb`. Without a server the
  engine and tests run unaffected (graph operations degrade gracefully).

## Determinism guarantees

- One seeded `numpy.random.Generator(PCG64)` stream, threaded explicitly; no
  stdlib `random`, no wall-clock, no unseeded numpy anywhere in the engine.
- Sub-streams are derived by hashing a label into a child seed (BLAKE2b), so
  they're independent of `PYTHONHASHSEED`.
- Every frozen artifact (scenario, battery, run manifest) is content-addressed
  with BLAKE2b over a canonical JSON serialisation.
- Verified by the test suite: same seed → byte-identical transcript and score,
  including across separate processes.

See `docs/DETERMINISM.md` and `docs/ARCHITECTURE.md` for details.

## Tests

```bash
uv run pytest
```

86 tests (2 skip without a FalkorDB server) cover RNG determinism, full
52-family coverage, scenario content-addressing, overlay expansion, multistep
precondition enforcement, factsheet-only answering, impossible-ask declines,
loop/turn-budget termination, the fail-closed classifier, score separation
across merchant tiers, persona cross-product, transcript replay, graph-driven
scenario generation, the FalkorDB backend (Cypher validated with a fake client),
and cross-process reproducibility.

## Layout

```
shopper_sim/
  engine/        rng (seeded stream), hashing (content-addressing), types
  taxonomy/      registry (52 families), graph (journey graph), scenario_compiler
                 (incl. graph-driven journeys), falkor_store (FalkorDB backend)
  persona/       library (8 personas), behavior (Markov + decision models)
  nlg/           lexicon, paraphrase_bank (frozen), realizer (no-LLM surface text)
  adapters/      base, turn_classifier, dialogue_policy (the multistep core),
                 mock_merchant, agent_adapter (httpx/MCP), web_adapter (Playwright)
  oracle/        rubric, scorer (deterministic)
  orchestrator/  runner (battery + persona modes + K-repeat variance + manifest)
  reporting/     scorecard, generation diff
tests/           86 tests (2 skip without a FalkorDB server)
examples/        run_full_battery, generation_diff, grade_real_agent, show_multistep_dialogue
docs/            ARCHITECTURE, DETERMINISM, MULTISTEP
```

## Scope of this build

This is a complete, runnable reference engine (~3,900 LOC engine + ~1,000 LOC
tests) with the determinism spine, full taxonomy with overlay expansion,
graph-driven and curated multistep scenarios, the multistep dialogue policy,
deterministic scoring, persona cross-product orchestration, transcript replay,
and reporting all working end-to-end against mock merchants. The journey graph
has a FalkorDB authoring backend (sync/load/query) that stays off the runtime
path.

The real-merchant transports (`HTTPAgentAdapter`, `PlaywrightWebAdapter`) are
structurally complete; wiring them to a specific merchant is a matter of
supplying the endpoint contract or page model.

Still on the production path and intentionally out of scope here: scoring tiers
2–3 (frozen-embedding semantic match and the frozen, cached LLM judge for open
free-text quality — tier 1 structural scoring is implemented), an explicit
`Expectation` node model with DOM/JSON assertion library, the web adapter's
selector auto-mapper, and the service layer (Postgres, object store, FastAPI,
Temporal, leaderboard/percentile). The engine runs without any of them.
