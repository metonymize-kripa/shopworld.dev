# Vending-Bench 2 Local Ollama Reproduction Harness

This zip contains a `uv run`-executable local harness for testing local Ollama models on a Vending-Bench-2-style long-horizon vending-machine business benchmark.

## Important limitation

Andon Labs’ public Vending-Bench 2 page describes the benchmark protocol and leaderboard, but it does not publish an official Vending-Bench 2 runner, dataset, supplier simulator, or exact traces. This project is therefore a local, deterministic reproduction harness built from the public benchmark description, not an official Andon Labs implementation.

Use it to prove that you can:

1. Run a year-long agentic vending-business simulation locally.
2. Execute local Ollama models through `uv run`.
3. Produce reproducible run traces, run summaries, aggregate reports, seed/config hashes, and a deterministic scripted baseline.
4. Compare local model behavior under a source-linked protocol.

Do not claim official leaderboard reproduction unless Andon Labs releases the official environment or grants access to it.

## Source-linked benchmark parameters implemented

The local harness implements these publicly described Vending-Bench 2 elements:

- Year-long simulated vending-machine business.
- Final score is bank account balance after one year.
- $500 starting bank balance.
- $2 daily operating/location fee.
- Early termination after failure to pay the fee for more than 10 consecutive days.
- Supplier discovery, email negotiation, adversarial/high-price suppliers, unreliable suppliers, and delivery delays.
- Storage inventory, vending-machine inventory, machine stocking, prices, cash collection, notes, and reminders.
- Daily sales driven by price elasticity, reference prices, base sales, day-of-week, month/season, weather, product variety, random noise, and inventory caps.
- Output-token cost charged at $100 per million estimated output tokens.

See `SOURCE_NOTES.md` for the public sources used.

## Requirements

- Python 3.11+
- `uv`
- Ollama running locally
- At least one pulled local Ollama model

Example model setup:

```bash
ollama serve
ollama pull gemma4:12b-mlx
```

## Unzip and run

```bash
unzip vending-bench-2-ollama-repro.zip
cd vending-bench-2-ollama-repro
uv sync
```

> [!NOTE]
> The lockfile was updated to use the public PyPI index (`https://pypi.org/simple`). If you ever need to manually override/refresh the index, run `uv sync --index-url https://pypi.org/simple`.

Check connectivity:

```bash
uv run vb2 doctor --model gemma4:12b-mlx
```

Run a quick local smoke test with a real Ollama model:

```bash
uv run vb2 run \
  --model gemma4:12b-mlx \
  --runs 1 \
  --days 14 \
  --max-steps 120 \
  --out-dir results/smoke
```

Run the deterministic non-LLM baseline to verify the harness is reproducible:

```bash
uv run vb2 run \
  --scripted-baseline \
  --runs 1 \
  --days 14 \
  --max-steps 120 \
  --out-dir results/baseline
```

Generate a report:

```bash
uv run vb2 report --results-dir results/baseline --out results/baseline/report.md
```

Run a 5-seed full-horizon local evaluation:

```bash
uv run vb2 run \
  --model gemma4:12b-mlx \
  --runs 5 \
  --days 365 \
  --max-steps 3000 \
  --seed-base 42 \
  --temperature 0.2 \
  --num-ctx 32768 \
  --max-output-tokens 1024 \
  --out-dir results/gemma4_12b_full

uv run vb2 report \
  --results-dir results/gemma4_12b_full \
  --out results/gemma4_12b_full/report.md
```

## Native tool calling vs JSON action mode

Default mode uses strict JSON action prompting because it works across most Ollama models:

```json
{"tool":"get_balance_and_transactions","arguments":{"n":20}}
```

Models with reliable native tool-calling support can use:

```bash
uv run vb2 run --model gemma4:12b-mlx --native-tools --runs 1 --days 30
```

## Outputs

Each run creates:

- `*.jsonl`: full event trace with step, date, tool call, tool result, score so far.
- `*.summary.json`: final score, config hash, tool counts, output tokens, units sold, termination reason.
- `report.md`: aggregate Markdown report.
- `report.csv`: aggregate CSV report.

Primary score:

```text
final_balance
```

Diagnostics also reported:

```text
machine_cash_uncollected
inventory_value_at_cost
net_worth_diagnostic
units_sold
tool_counts
invalid_actions
```

## Interpretation

A useful local result package should include:

1. The model name and Ollama tag.
2. The exact command used.
3. The config hash from each summary.
4. The five seed summaries.
5. The aggregate `report.md` and `report.csv`.
6. The raw JSONL traces.

## Development checks

```bash
uv run pytest
```

## Files

```text
configs/vb2_local.json        Benchmark config
benchmarks/official_vb2_leaderboard_snapshot_2026-06-29.json  Public leaderboard context snapshot
src/vb2_local/sim.py          Deterministic business simulator and tools
src/vb2_local/agent.py        Ollama client, JSON action parser, scripted baseline
src/vb2_local/runner.py       Run orchestration and report builder
src/vb2_local/cli.py          CLI entry point: vb2
tests/test_sim.py             Basic reproducibility tests
scripts/run_smoke.sh          One-run smoke command
scripts/run_5x_full.sh        Five-run full-horizon command
SOURCE_NOTES.md               Public-source notes and limitation statement
```
