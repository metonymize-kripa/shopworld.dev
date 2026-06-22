#!/usr/bin/env python3
"""Run the MVP benchmark and emit the comparative failure-taxonomy report.

README §12 step 13 (failure taxonomy report) + §13 (report separates milli.run
failures from LLM failures, NLU benchmark reported separately).

Usage:
    python experiments/compare_agents.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from shopworld.bench import run_benchmark  # noqa: E402
from shopworld.bench.compare import build_markdown  # noqa: E402
from shopworld.tasks import mvp_task_set  # noqa: E402


def _nlu_section() -> str:
    """milli.run NLU benchmark on the held-out Bitext split (README §9 NLU layer)."""
    try:
        from shopworld.scenarios import import_support_utterances
        from shopworld.scenarios.splits import Split
        from milli_run.nlu.svm_model import LinearIntentClassifier
        from milli_run.nlu.entity_extractor import EntityExtractor
        from milli_run.nlu.corpus import augmented_training
    except Exception as exc:  # noqa: BLE001
        return f"## NLU benchmark\n\nUnavailable: {exc}\n"

    clf = LinearIntentClassifier(training=augmented_training(), epochs=200)
    labels = {"WISMO", "CANCEL", "REFUND", "RETURN", "ADDRESS_CHANGE"}
    heldout = [
        u for u in import_support_utterances()
        if u.split == Split.HELDOUT_TEST and u.intent in labels
    ]
    correct = sum(1 for u in heldout if clf.predict(u.text).label == u.intent)
    acc = correct / len(heldout) if heldout else 0.0

    ex = EntityExtractor()
    ents = ex.extract("Refund $42.50 for order-7, email a@b.com")
    entity_ok = bool(ents.amounts and ents.emails and ents.order_ref)

    return (
        "## NLU benchmark (milli.run)\n\n"
        f"- Held-out intent accuracy: {acc:.0%} on {len(heldout)} utterances "
        "(trained on built-in + Bitext nlu_train split; evaluated on disjoint "
        "held-out split per the leakage rule).\n"
        f"- Entity extraction sanity (amount/email/order-ref): {'pass' if entity_ok else 'fail'}.\n\n"
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comparative agent report")
    parser.add_argument("--seeds", type=str, default="1,2,3")
    parser.add_argument(
        "--out-dir", type=Path, default=Path(__file__).resolve().parent / "reports"
    )
    args = parser.parse_args(argv)
    seeds = [int(s) for s in args.seeds.split(",")]

    # Build agent registry (skip unavailable agents gracefully).
    from shopworld.agents import BaselineAgent

    registry = {"baseline": BaselineAgent}
    try:
        from milli_run import MilliRunAgent

        registry["milli_run"] = MilliRunAgent
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] milli_run: {exc}", file=sys.stderr)
    try:
        from llm_agent import LLMAgent

        registry["llm_agent"] = LLMAgent
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] llm_agent: {exc}", file=sys.stderr)

    tasks = mvp_task_set()
    print(f"Running {len(tasks)} scenarios x {len(seeds)} seeds x {len(registry)} agents...")
    bench = run_benchmark(tasks, registry, seeds=seeds)

    markdown = build_markdown(bench, nlu_section=_nlu_section())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparative_report.md").write_text(markdown)
    (args.out_dir / "results.json").write_text(json.dumps(bench.to_dict(), indent=2))

    print(markdown)
    print(f"\nReport: {args.out_dir / 'comparative_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
