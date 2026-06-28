"""Example: grade a REAL merchant chat agent over HTTP.

This shows how to plug your own merchant endpoint into the simulator. The
shopper side stays fully deterministic; only your endpoint introduces variance,
which the K-repeats measure.

    python examples/grade_real_agent.py https://your-merchant.example/chat

Your endpoint should accept JSON {"message": ..., "session_id": ..., "history": [...]}
and return JSON {"reply": "..."}. If your contract differs, pass custom
``request_builder`` / ``response_parser`` callables to HTTPAgentAdapter.
"""

from __future__ import annotations

import sys

from shopper_sim.adapters.agent_adapter import HTTPAgentAdapter
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas
from shopper_sim.reporting.scorecard import format_scorecard
from shopper_sim.taxonomy.registry import HARD_CORE_MULTISTEP
from shopper_sim.taxonomy.scenario_compiler import compile_family_scenario


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python examples/grade_real_agent.py <endpoint-url>")
        raise SystemExit(2)
    endpoint = sys.argv[1]

    # Grade only the hard-core multistep families -- the ones single-shot
    # graders cannot measure. Swap in compile_full_battery() for everything.
    scenarios = [compile_family_scenario(fid) for fid in sorted(HARD_CORE_MULTISTEP)]

    run = run_battery(
        scenarios=scenarios,
        personas=all_personas(),
        adapter_factory=lambda s: HTTPAgentAdapter(endpoint),
        k_repeats=3,
        battery_version="real-agent-multistep-1",
    )
    print(format_scorecard(run))


if __name__ == "__main__":
    main()
