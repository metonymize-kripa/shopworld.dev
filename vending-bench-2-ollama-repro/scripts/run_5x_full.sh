#!/usr/bin/env bash
set -euo pipefail
MODEL="${1:-qwen2.5:7b-instruct}"
OUT="results/${MODEL//[:\/]/_}_full"
uv run vb2 doctor --model "$MODEL"
uv run vb2 run --model "$MODEL" --runs 5 --days 365 --max-steps 3000 --seed-base 42 --temperature 0.2 --num-ctx 32768 --max-output-tokens 1024 --out-dir "$OUT"
uv run vb2 report --results-dir "$OUT" --out "$OUT/report.md"
