# shopworld.dev — Evaluation Suite for Agentic Commerce

`shopworld.dev` is an evaluation suite and simulator sandbox for testing AI agents operating on commerce workflows. The repository focuses on two core subsystems: a deterministic shopper behavioral simulator (`shopper_sim`) and an Amazon-like Gym reinforcement learning environment (`commerce_rle`), backed by a public-facing developer web dashboard at the root.

Before a merchant gives an agent write access, the agent should prove it can make profitable, policy-safe commerce decisions in a deterministic sandbox.

---

## Repository Map

| Area | Role | Status |
| --- | --- | --- |
| **Root Web App** (`src/`, `public/`) | Public-facing developer landing page and interactive "Game Sims" playground enclosing the Agent Sprint and Support Simulator. | Active portal. |
| [**`shopper_sim/`**](file:///Users/kripar/Documents/coding/shopworld.dev/shopper_sim) | Fully deterministic, LLM-free shopper behavioral engine grading storefronts and agents against 52 macro query families. | Active subproject. |
| [**`commerce_rle/`**](file:///Users/kripar/Documents/coding/shopworld.dev/commerce_rle) | Bounded Amazon-commerce Gym reinforcement learning environment featuring state-diff checks, no-op labeling, and field-level collateral-damage penalties. | Active subproject. |
| [**`vending-bench-2-ollama-repro/`**](file:///Users/kripar/Documents/coding/shopworld.dev/vending-bench-2-ollama-repro) | Vending-Bench 2 Local Ollama Reproduction Harness for testing local LLMs on a long-horizon vending business simulation. | Active subproject. |

---

## Canonical Commands

Use the root `Makefile` for web application workflows:

| Command | Purpose |
| --- | --- |
| `make app-dev` | Start the Vite local development server. |
| `make app-build` | Build the production web bundle. |
| `make app-preview` | Preview the production build locally. |
| `make check` | Run production build validation checks. |

---

## Local Development

### 1. Web Application

Install dependencies and start the Vite environment:
```bash
npm install
npm run dev
```

### 2. Shopper Simulator

Execute the shopper simulator matrix tests:
```bash
cd shopper_sim
uv run python -m pytest -q
```

### 3. Commerce RL Environment

Execute the Gym environment benchmarks:
```bash
cd commerce_rle
uv run pytest -q
```

### 4. Vending-Bench 2 Ollama Repro

Local evaluation harness for testing Ollama models on a vending-machine business simulation. For more detail, read the [Vending-Bench 2 README](file:///Users/kripar/Documents/coding/shopworld.dev/vending-bench-2-ollama-repro/README.md) and [SOURCE_NOTES.md](file:///Users/kripar/Documents/coding/shopworld.dev/vending-bench-2-ollama-repro/SOURCE_NOTES.md).

Run unit tests:
```bash
cd vending-bench-2-ollama-repro
uv run pytest -q
```

Run a quick local smoke test with a model (e.g. `gemma4:12b-mlx`):
```bash
cd vending-bench-2-ollama-repro
uv run vb2 run --model gemma4:12b-mlx --runs 1 --days 14 --max-steps 120 --out-dir results/smoke
```

---

## License

Apache-2.0
