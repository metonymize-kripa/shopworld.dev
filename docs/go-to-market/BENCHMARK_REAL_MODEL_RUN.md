# Real-Model Benchmark — How to Run It, and What Has to Change Before You Publish

_Internal. Last updated: 2026-06-22._

**Problem.** The 270-episode comparative result is not publishable. The "LLM agent" in it is `ScriptedLLMClient` — a deterministic offline stand-in with no network and no model behind it. Scores are bucketed (every episode grades to 20 or 80). milli.run scores exactly 80 on all 270 runs, zero variance. The entire milli-vs-LLM gap is one workflow family — escalation/abuse — which the repo's own notes say was added "to create a fair milli.run-vs-LLM divergence," and which the scripted client has no branch to handle. Put `100% vs 83%` in front of a Salsify or Mars engineer and the first question — "which model, on what data?" — ends the conversation. So we hold the numbers and fix the test.

## Part 1 — Running against a real model (wired, ready)

The runner now accepts a real local Ollama model as an agent under test.

```bash
cd shopworld-platform
ollama serve                                # if the Ollama service is not already running
ollama ls                                   # confirm gemma4:12b-mlx is present
export SHOPWORLD_LLM_MODEL=gemma4:12b-mlx   # optional; this is the default
export OLLAMA_HOST=http://127.0.0.1:11434   # optional; this is the default

uv run python experiments/run_benchmark.py \
  --config experiments/configs/mvp_real_llm.yaml \
  --out experiments/reports/results_real_llm.json
```

What changed: `experiments/run_benchmark.py` gained an `llm_agent_ollama` registry branch (aliases: `llm_agent_local`, `llm_agent_real`) that builds `LLMAgent(client=OllamaClient(model=...))`. The adapter talks to Ollama's local HTTP API, validates that the server is reachable and `gemma4:12b-mlx` is pulled, and skips cleanly (not fatal) if either check fails — so without a running local model you get a milli-only run and a one-line notice. `experiments/configs/mvp_real_llm.yaml` runs `milli_run` vs `llm_agent_ollama`. Nothing about the neutral runner or the evaluator changed; the model just replaces the scripted stand-in behind the same `LLMClient` interface.

This makes a real head-to-head one command. It does **not** by itself make the result publishable — Part 2 does.

## Part 2 — Why a real-model run still isn't enough

Swapping in a real model removes the biggest objection but leaves four that a sharp buyer will still raise.

*Self-authored scenarios.* The six families were written by us, and milli.run's NLU and state machines were built against them. milli is being graded on its own training distribution. A real model run on the same 30 scenarios still measures "milli on home turf."

*The escalation family is load-bearing and possibly unfair.* It is the only thing separating the agents, and it was added to produce a gap. The scripted client fails it because it has no escalation branch — not because real models can't escalate. A real model with a system prompt that states the escalation policy may well handle it. If we don't give the LLM that prompt, we're testing "did we tell it the rule," not capability. Either outcome is fine to report; hiding the prompt is not.

*Coarse grading.* A 20/80 rubric can't show nuance — partial credit, quality differences, or how close a miss was. milli scoring 80 on all 270 with zero variance is a rubric artifact, not a finding.

*One tradeoff we currently bury: cost.* milli.run averages ~3.2 tool calls per episode vs ~2.5 for the LLM stand-in. It is *more* API-expensive because it checks more before acting. That's a defensible tradeoff — report it, don't hide it.

## Part 3 — What to change before publishing a number

In priority order.

- **Held-out scenarios milli never saw.** Build a test split from sources milli was not tuned on — Bitext ticket logs, real anonymized support transcripts, scenarios written by someone other than the milli author. Freeze it. milli's NLU training split must not overlap it (the §6 leakage rule already exists for NLU; extend the discipline to whole scenarios).
- **Give the LLM a fair, documented prompt.** Expose `tickets.escalate` and `policy.lookup`, and state the escalation/refund policy in its system prompt exactly as milli's guards encode it. Publish the prompt alongside results. The honest claim is "milli enforces the policy deterministically; the model follows it probabilistically," not "the model didn't know the rule."
- **Widen grading and add human review.** Replace or supplement the 20/80 buckets with graded partial credit, and have a human grade a random sample blind to which agent produced each trace. Report agreement.
- **Report distributions, not point estimates.** Per-family success, score spread, variance across seeds, and API cost per agent. A table with confidence intervals reads as science; a single `100%` reads as marketing.
- **Pre-register the hypothesis.** State up front what you expect — milli stronger on policy/escalation/auditability, the model stronger on novel language and open dialogue — so the result reads as a test, not a sales artifact. This is also the honest framing: the two are complements, not a knockout.
- **Run enough episodes for significance.** 30 scenarios × 3 seeds is fine for a smoke test, thin for a published claim. Scale scenarios and seeds until per-family numbers are stable.

## Part 4 — What you can already say truthfully (no run required)

While the above is in progress, these hold without a benchmark and belong on the client page as-is:

- milli.run runs covered workflows as deterministic software: millisecond latency, no per-action token cost.
- Every action carries a reason and a rollback — an audit trail a non-engineer can read.
- It learns from the merchant's own tickets and policies.
- Hard guards block unsafe writes and escalate fraud/abuse by construction, not by best effort.
- The held-out NLU intent accuracy (94% on a disjoint Bitext split) is a real, leakage-controlled measurement and is fair to cite — it's milli's own capability, not a head-to-head.

## TL;DR

Local real-model run is wired (`mvp_real_llm.yaml`, one `uv run` command). But a publishable claim needs held-out scenarios milli wasn't built on, a fair documented prompt for the model, graded-with-human-review scoring, distributions over point estimates, and a pre-registered hypothesis. Until then, sell the architecture (speed, audit, guards, learnability, cost) — all true today — and show the failure mode as an illustrative example, not a measured score.
