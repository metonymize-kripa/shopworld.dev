from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import OllamaError
from .runner import build_report, doctor, run_many


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vb2", description="Local Vending-Bench 2 reproduction harness for Ollama models")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="Check Ollama connectivity and available local models")
    p_doctor.add_argument("--ollama-host", default="http://localhost:11434")
    p_doctor.add_argument("--model", default=None)

    p_run = sub.add_parser("run", help="Run local Vending-Bench 2 harness")
    p_run.add_argument("--model", default="llama3.1:8b", help="Ollama model name, e.g. qwen2.5:7b-instruct")
    p_run.add_argument("--runs", type=int, default=1)
    p_run.add_argument("--seed-base", type=int, default=42)
    p_run.add_argument("--days", type=int, default=365)
    p_run.add_argument("--max-steps", type=int, default=2500)
    p_run.add_argument("--out-dir", default="results")
    p_run.add_argument("--config", default="configs/vb2_local.json")
    p_run.add_argument("--ollama-host", default="http://localhost:11434")
    p_run.add_argument("--temperature", type=float, default=0.2)
    p_run.add_argument("--num-ctx", type=int, default=32768)
    p_run.add_argument("--max-output-tokens", type=int, default=1024)
    p_run.add_argument("--native-tools", action="store_true", help="Use Ollama native tool-calling instead of JSON-only action prompting")
    p_run.add_argument("--scripted-baseline", action="store_true", help="Use deterministic non-LLM baseline for harness verification")

    p_report = sub.add_parser("report", help="Aggregate run summaries into Markdown and CSV")
    p_report.add_argument("--results-dir", default="results")
    p_report.add_argument("--out", default="results/report.md")

    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(doctor(args.ollama_host, args.model), indent=2))
            return 0
        if args.command == "run":
            summaries = run_many(
                model=args.model,
                runs=args.runs,
                seed_base=args.seed_base,
                days=args.days,
                max_steps=args.max_steps,
                out_dir=args.out_dir,
                config_path=args.config,
                ollama_host=args.ollama_host,
                temperature=args.temperature,
                num_ctx=args.num_ctx,
                max_output_tokens=args.max_output_tokens,
                native_tools=args.native_tools,
                scripted_baseline=args.scripted_baseline,
            )
            print(json.dumps({"runs": summaries}, indent=2))
            return 0
        if args.command == "report":
            report = build_report(args.results_dir, args.out)
            print(report)
            return 0
    except OllamaError as exc:
        print(f"Ollama error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
