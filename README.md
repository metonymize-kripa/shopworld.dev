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

Set up and execute the shopper simulator matrix tests:
```bash
cd shopper_sim
pip install -e ".[dev]"
pytest -q
```

### 3. Commerce RL Environment

Set up and execute the Gym environment benchmarks:
```bash
cd commerce_rle
pip install -e ".[dev]"
pytest -q
```

---

## License

Apache-2.0
