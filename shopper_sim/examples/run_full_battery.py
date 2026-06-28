"""Example: run the full 52-family battery against a mock merchant.

Run from the repo root:

    python examples/run_full_battery.py

Swap ``GoodMerchant`` for your own adapter (see adapters/agent_adapter.py)
to grade a real merchant.
"""

from __future__ import annotations

from shopper_sim.adapters.mock_merchant import GoodMerchant
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas
from shopper_sim.reporting.scorecard import format_scorecard
from shopper_sim.taxonomy.scenario_compiler import compile_full_battery


def main() -> None:
    scenarios = compile_full_battery()
    print(f"Compiled {len(scenarios)} scenarios (52 families, overlays expanded).")

    run = run_battery(
        scenarios=scenarios,
        personas=all_personas(),
        adapter_factory=lambda s: GoodMerchant(s),
        k_repeats=5,
        battery_version="example-full-1",
    )
    print()
    print(format_scorecard(run))


if __name__ == "__main__":
    main()
