#!/usr/bin/env bash
set -euo pipefail
MODEL="${1:-qwen2.5:7b-instruct}"
uv run vb2 doctor --model "$MODEL"
uv run vb2 run --model "$MODEL" --runs 1 --days 14 --max-steps 120 --out-dir results/smoke
uv run vb2 report --results-dir results/smoke --out results/smoke/report.md
