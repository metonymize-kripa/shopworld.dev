# Determinism

The product's value is a *stable ruler*: a merchant must be able to compare
gen-N against gen-N+1 and trust that any score change came from their merchant,
not from the test harness. That requires the shopper side to be a pure function
of `(scenario, persona, seed)`.

## The rules

1. **One seeded stream.** All randomness comes from a single
   `numpy.random.Generator(PCG64(seed))`, wrapped in `DeterministicRNG` and
   threaded explicitly through every stochastic call.
2. **No stdlib `random`.** It is never imported in the engine.
3. **No unseeded numpy.** Never `np.random.*` against the global generator.
4. **No wall clock.** No `time.time()`, `datetime.now()`, or anything that reads
   ambient state inside the engine.
5. **Order before sampling.** Never sample from a `set` or rely on `dict`
   iteration order for anything stochastic; inputs are ordered sequences.
6. **Content-address everything frozen.** Scenarios, batteries, and run
   manifests hash their canonical JSON with BLAKE2b.

## Sub-streams

Independent subsystems need independent randomness without interfering. A child
stream is derived by hashing the parent seed and a label:

```python
child = rng.derive("behavior")   # != rng.derive("nlg")
```

`derive_seed` uses BLAKE2b, not Python's `hash()`, so derivation is stable
across processes and unaffected by `PYTHONHASHSEED`.

## Why content hashes are stable

`content_hash` serialises with `json.dumps(obj, sort_keys=True,
separators=(",", ":"))`. Sorted keys + no insignificant whitespace mean two
semantically identical artifacts always hash identically, regardless of dict
construction order. This is verified across `PYTHONHASHSEED` values in the
scenario-compiler tests.

## What's deterministic vs not

| Component | Deterministic? |
|-----------|----------------|
| Shopper utterances, decisions, dialogue trajectory | Yes — pure function of `(scenario, persona, seed)` |
| Scenario compilation + ids | Yes — content-addressed |
| Scoring | Yes — pure function of the transcript |
| The merchant under test | **No** — this is the thing being measured |

Because only the merchant introduces variance, running each scenario K times
(each with a different shopper *phrasing* but the same goal structure) and
reporting the score distribution cleanly attributes any inconsistency to the
merchant.

## The K-repeat subtlety

K-repeats deliberately use *different* seeds so the shopper phrases the same
goal differently each time (terse vs polite, different paraphrase). This probes
whether the merchant is robust to phrasing. So:

- **Per-seed**: byte-identical. Re-running the exact same battery reproduces
  every per-scenario score (`test_per_repeat_scores_are_individually_reproducible`).
- **Across the K repeats of one scenario**: scores may differ slightly if the
  merchant responds differently to different phrasings — and with a deterministic
  mock merchant the spread stays small. A large spread flags a merchant that is
  itself unstable.

## Enforcement in production

A ruff plugin bans `random.`, `time.time`, `datetime.now`, and bare
`np.random.` inside the engine and runtime path. An import-linter contract
forbids the `engine`/runtime packages from importing any LLM SDK or the
authoring tooling. A battery run records the engine git SHA and a frozen
dependency lock in its manifest so a score is reproducible against an exact
build.
