"""Command-line interface for the shopper simulator.

Usage:
    python -m shopper_sim.cli coverage
    python -m shopper_sim.cli run [--merchant good|clueless|overeager] [--k N]
    python -m shopper_sim.cli demo-diff
"""

from __future__ import annotations

import argparse
import json
import sys

from .adapters.mock_merchant import (
    CluelessMerchant,
    GoodMerchant,
    OvereagerMerchant,
)
from .orchestrator.runner import run_battery
from .persona.library import all_personas
from .reporting.scorecard import diff_runs, format_diff, format_scorecard
from .taxonomy.registry import HARD_CORE_MULTISTEP, all_families
from .taxonomy.scenario_compiler import compile_full_battery

_MERCHANTS = {
    "good": GoodMerchant,
    "clueless": CluelessMerchant,
    "overeager": OvereagerMerchant,
}


def cmd_coverage(_args: argparse.Namespace) -> int:
    families = all_families()
    print(f"Total macro families: {len(families)}")
    multistep = [f for f in families if f.is_multistep]
    print(f"Multistep families:   {len(multistep)}")
    print(f"Hard-core multistep:  {len(HARD_CORE_MULTISTEP)}")
    print()
    for f in families:
        tag = "M" if f.is_multistep else "S"
        core = "*" if f.id in HARD_CORE_MULTISTEP else " "
        print(f"  {f.number:>2} [{tag}{core}] {f.id:<24} {f.layer.value:<12} {f.name}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    merchant_cls = _MERCHANTS[args.merchant]
    scenarios = compile_full_battery(expand_overlays=not args.no_overlays)
    run = run_battery(
        scenarios=scenarios,
        personas=all_personas(),
        adapter_factory=lambda s: merchant_cls(s),
        k_repeats=args.k,
        battery_version="cli-full-1",
        persona_mode=args.persona_mode,
        capture_transcripts=bool(args.dump_transcripts),
    )
    if args.dump_transcripts:
        with open(args.dump_transcripts, "w", encoding="utf-8") as fh:
            json.dump(run.as_dict(), fh, indent=2)
        print(f"Wrote full run with transcripts to {args.dump_transcripts}")
        print(f"  scenarios={len(scenarios)} cells={len(run.distributions)} "
              f"headline={run.headline * 100:.1f}")
    elif args.json:
        print(json.dumps(run.as_dict(), indent=2))
    else:
        print(format_scorecard(run))
    return 0


def cmd_demo_diff(_args: argparse.Namespace) -> int:
    scenarios = compile_full_battery()
    before = run_battery(
        scenarios, all_personas(),
        adapter_factory=lambda s: CluelessMerchant(s),
        k_repeats=3, battery_version="diff-demo",
    )
    after = run_battery(
        scenarios, all_personas(),
        adapter_factory=lambda s: GoodMerchant(s),
        k_repeats=3, battery_version="diff-demo",
    )
    diff = diff_runs(before, after)
    print(format_diff(diff))
    return 0


def cmd_graph_sync(args: argparse.Namespace) -> int:
    from .taxonomy.falkor_store import FalkorConfig, FalkorJourneyStore

    store = FalkorJourneyStore(FalkorConfig(host=args.host, port=args.port))
    if not store.ping():
        print(f"No FalkorDB server reachable at {args.host}:{args.port}.")
        print("Start one with: docker run -p 6379:6379 -it --rm falkordb/falkordb")
        return 1
    count = store.sync()
    print(f"Synced journey graph to FalkorDB graph '{store._config.graph_name}': "
          f"{count} edges across 52 families.")
    if args.show_into:
        paths = store.journeys_into(args.show_into)
        print(f"\nPrerequisite journeys into '{args.show_into}':")
        for p in paths[:20]:
            print("  " + " -> ".join(p))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shopper_sim")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("coverage", help="print the 52-family coverage matrix")

    run_p = sub.add_parser("run", help="run the battery against a mock merchant")
    run_p.add_argument("--merchant", choices=list(_MERCHANTS), default="good")
    run_p.add_argument("--k", type=int, default=5, help="repeats per scenario")
    run_p.add_argument("--persona-mode", choices=["recommended", "cross"],
                       default="recommended",
                       help="'cross' runs every scenario against every persona")
    run_p.add_argument("--no-overlays", action="store_true",
                       help="compact 52-scenario battery (one per family)")
    run_p.add_argument("--json", action="store_true", help="emit JSON")
    run_p.add_argument("--dump-transcripts", metavar="PATH",
                       help="write the full run incl. per-turn transcripts to PATH")

    sub.add_parser("demo-diff", help="show a generation diff (clueless -> good)")

    g = sub.add_parser("graph-sync", help="sync the journey graph into FalkorDB")
    g.add_argument("--host", default="localhost")
    g.add_argument("--port", type=int, default=6379)
    g.add_argument("--show-into", metavar="FAMILY",
                   help="after sync, print prerequisite journeys into FAMILY")

    args = parser.parse_args(argv)
    if args.command == "coverage":
        return cmd_coverage(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "demo-diff":
        return cmd_demo_diff(args)
    if args.command == "graph-sync":
        return cmd_graph_sync(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
