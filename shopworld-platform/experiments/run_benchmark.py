#!/usr/bin/env python3
"""Run the ShopWorld MVP benchmark (README §12 step 12).

Neutral entrypoint: it builds the scenario set and an agent registry, then hands
both to the agent-blind runner. Agents that fail to import (missing optional deps,
no API key) are skipped with a notice rather than aborting the run.

Usage:
    python experiments/run_benchmark.py [--config experiments/configs/mvp_30.yaml]
    python experiments/run_benchmark.py --agents baseline,milli_run --seeds 1,2,3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

# Make src/ importable whether run from repo root or elsewhere.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from shopworld.agents import Agent, BaselineAgent, NoOpAgent  # noqa: E402
from shopworld.bench import run_benchmark  # noqa: E402
from shopworld.tasks import mvp_task_set  # noqa: E402


def build_agent_registry(names: List[str]) -> Dict[str, Callable[[], Agent]]:
    """Resolve agent names to factories, skipping any that won't import.

    milli.run and the LLM agent live in sibling packages the runner never imports
    directly (README §13). We import them lazily here, in the neutral entrypoint.
    """
    registry: Dict[str, Callable[[], Agent]] = {}
    for name in names:
        if name == "baseline":
            registry["baseline"] = BaselineAgent
        elif name == "noop":
            registry["noop"] = NoOpAgent
        elif name == "milli_run":
            try:
                from milli_run import MilliRunAgent

                registry["milli_run"] = MilliRunAgent
            except Exception as exc:  # noqa: BLE001
                print(f"[skip] milli_run unavailable: {exc}", file=sys.stderr)
        elif name == "llm_agent":
            try:
                from llm_agent import LLMAgent

                registry["llm_agent"] = LLMAgent
            except Exception as exc:  # noqa: BLE001
                print(f"[skip] llm_agent unavailable: {exc}", file=sys.stderr)
        elif name in ("llm_agent_anthropic", "llm_agent_real"):
            # Real frontier model under test (not the offline ScriptedLLMClient).
            # Requires `pip install anthropic` and ANTHROPIC_API_KEY. Model is
            # configurable via SHOPWORLD_LLM_MODEL. We construct one client now to
            # validate prerequisites and skip (not abort) if they are missing.
            try:
                import os

                from llm_agent import LLMAgent
                from llm_agent.client import AnthropicClient

                model = os.environ.get("SHOPWORLD_LLM_MODEL", "claude-sonnet-4-6")
                AnthropicClient(model=model)  # validate SDK + API key up front
                registry[name] = lambda model=model: LLMAgent(client=AnthropicClient(model=model))
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[skip] {name} unavailable (need `pip install anthropic` + "
                    f"ANTHROPIC_API_KEY): {exc}",
                    file=sys.stderr,
                )
        else:
            print(f"[skip] unknown agent: {name}", file=sys.stderr)
    return registry


def load_config(path: Path) -> Dict[str, Any]:
    defaults = {"agents": ["baseline", "milli_run", "llm_agent"], "seeds": [1, 2, 3], "max_steps": 25}
    if not path or not path.exists():
        return defaults
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text()) or {}
        defaults.update({k: v for k, v in data.items() if v is not None})
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not parse {path} ({exc}); using defaults", file=sys.stderr)
    return defaults


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ShopWorld MVP benchmark")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--agents", type=str, default=None, help="comma-separated agent names")
    parser.add_argument("--seeds", type=str, default=None, help="comma-separated seeds")
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "reports" / "results.json"
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.agents:
        config["agents"] = args.agents.split(",")
    if args.seeds:
        config["seeds"] = [int(s) for s in args.seeds.split(",")]
    if args.max_steps:
        config["max_steps"] = args.max_steps

    tasks = mvp_task_set()
    registry = build_agent_registry(config["agents"])
    if not registry:
        print("No agents available to run.", file=sys.stderr)
        return 1

    print(
        f"Running {len(tasks)} scenarios x {len(config['seeds'])} seeds x "
        f"{len(registry)} agents = "
        f"{len(tasks) * len(config['seeds']) * len(registry)} episodes..."
    )
    bench = run_benchmark(tasks, registry, seeds=config["seeds"], max_steps=config["max_steps"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bench.to_dict(), indent=2))

    # Console summary.
    print("\nAgent             scenarios  success   avg_score")
    print("-" * 50)
    for agent in bench.agents():
        eps = bench.by_agent(agent)
        n = len(eps)
        succ = sum(1 for e in eps if e.success)
        avg = sum(e.overall_score for e in eps) / n if n else 0.0
        print(f"{agent:<16}  {n:>8}  {succ:>6}/{n:<3}  {avg:>8.1f}")
    print(f"\nResults written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
