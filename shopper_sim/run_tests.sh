#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Running shopper_sim test suite"
uv run pytest "$@"
