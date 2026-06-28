"""Example: compare two merchant "generations" on the identical frozen battery.

Simulates the hill-climb loop the product is sold on: you run gen-N, ship a new
model, run gen-N+1 on the SAME battery, and diff. Regressions and improvements
are attributed per scenario.

    python examples/generation_diff.py
"""

from __future__ import annotations

from shopper_sim.adapters.mock_merchant import CluelessMerchant, GoodMerchant
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas
from shopper_sim.reporting.scorecard import diff_runs, format_diff
from shopper_sim.taxonomy.scenario_compiler import compile_full_battery


def main() -> None:
    scenarios = compile_full_battery()
    personas = all_personas()

    # Generation N: a weak merchant.
    gen_n = run_battery(
        scenarios, personas,
        adapter_factory=lambda s: CluelessMerchant(s),
        k_repeats=3, battery_version="gen-compare",
    )
    # Generation N+1: an improved merchant. Same battery_version => same ruler.
    gen_n1 = run_battery(
        scenarios, personas,
        adapter_factory=lambda s: GoodMerchant(s),
        k_repeats=3, battery_version="gen-compare",
    )

    diff = diff_runs(gen_n, gen_n1)
    print(format_diff(diff))


if __name__ == "__main__":
    main()
