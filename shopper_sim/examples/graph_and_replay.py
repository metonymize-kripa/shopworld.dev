"""Example: graph-driven scenarios, persona cross-product, and replay.

Shows the gap-closing features end to end:
  * compile an exploratory multistep scenario by walking the journey graph,
  * run a small battery across every persona (cross-product),
  * capture full transcripts and write them for replay.

    python examples/graph_and_replay.py
"""

from __future__ import annotations

import json

from shopper_sim.adapters.mock_merchant import GoodMerchant
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas
from shopper_sim.reporting.scorecard import format_scorecard
from shopper_sim.taxonomy.scenario_compiler import compile_graph_journey


def main() -> None:
    # 1. Graph-driven exploratory journeys from a few starting families.
    scenarios = [
        compile_graph_journey("category_discovery", seed=1),
        compile_graph_journey("order_confirmation", seed=2),
        compile_graph_journey("tracking", seed=3),
    ]
    for s in scenarios:
        steps = " -> ".join(g.family_id for g in s.goals)
        print(f"{s.title}\n  {steps}\n")

    # 2. Cross-product run with transcript capture.
    run = run_battery(
        scenarios, all_personas(),
        adapter_factory=lambda s: GoodMerchant(s),
        k_repeats=2,
        persona_mode="cross",
        capture_transcripts=True,
        battery_version="graph-journey-demo",
    )
    print(format_scorecard(run))

    # 3. Write the full run (incl. per-turn transcripts) for replay.
    with open("graph_run.json", "w", encoding="utf-8") as fh:
        json.dump(run.as_dict(), fh, indent=2)
    cells = len(run.distributions)
    print(f"\nWrote {cells} cells with transcripts to graph_run.json")


if __name__ == "__main__":
    main()
