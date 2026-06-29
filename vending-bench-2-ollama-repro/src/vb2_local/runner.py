from __future__ import annotations

import datetime as dt
import json
import statistics
import time
from pathlib import Path
from typing import Any

from .agent import OllamaAgent, OllamaClient, OllamaError, ScriptedBaselineAgent, ToolCall
from .sim import VendingBench2LocalSim, load_config, tool_names


def run_one(
    *,
    model: str,
    seed: int,
    days: int,
    max_steps: int,
    out_dir: str | Path,
    config_path: str | None = None,
    ollama_host: str = "http://localhost:11434",
    temperature: float = 0.2,
    num_ctx: int = 32768,
    max_output_tokens: int = 1024,
    native_tools: bool = False,
    scripted_baseline: bool = False,
) -> dict[str, Any]:
    cfg = load_config(config_path, seed=seed, max_days=days)
    sim = VendingBench2LocalSim(cfg)
    agent: Any
    if scripted_baseline:
        agent = ScriptedBaselineAgent()
        model_label = "scripted_baseline"
    else:
        agent = OllamaAgent(
            model=model,
            host=ollama_host,
            temperature=temperature,
            num_ctx=num_ctx,
            max_output_tokens=max_output_tokens,
            native_tools=native_tools,
        )
        model_label = model
    start = time.time()
    run_id = f"{safe_name(model_label)}_seed{seed}_{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}"
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_path / f"{run_id}.jsonl"
    summary_path = out_path / f"{run_id}.summary.json"
    last_result: dict[str, Any] | None = {"ok": True, "message": "Simulation started.", "data": sim.public_status()}
    events: list[dict[str, Any]] = []
    with jsonl_path.open("w", encoding="utf-8") as f:
        for step in range(1, max_steps + 1):
            if sim.done:
                break
            status = sim.public_status()
            call = agent.next_tool(status, last_result)
            if not scripted_baseline:
                sim.charge_output_tokens(call.raw_response or json.dumps({"tool": call.name, "arguments": call.arguments}))
            if call.parse_error:
                sim.invalid_actions += 1
            if call.name not in tool_names():
                tool_result = sim.call_tool("think", {"thought": f"Invalid tool requested: {call.name}. Raw response: {call.raw_response[:1000]}"})
            else:
                tool_result = sim.call_tool(call.name, call.arguments)
            public_result = tool_result.to_public()
            agent.observe_tool_result(public_result)
            last_result = public_result
            event = {
                "step": step,
                "day": sim.day,
                "date": str(sim.current_date),
                "model": model_label,
                "seed": seed,
                "tool": call.name,
                "arguments": call.arguments,
                "parse_error": call.parse_error,
                "tool_result": public_result,
                "score_so_far": sim.score(),
            }
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            events.append(event)
    elapsed = round(time.time() - start, 3)
    summary = {
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": model_label,
        "ollama_host": None if scripted_baseline else ollama_host,
        "seed": seed,
        "days_requested": days,
        "max_steps": max_steps,
        "temperature": None if scripted_baseline else temperature,
        "num_ctx": None if scripted_baseline else num_ctx,
        "max_output_tokens": None if scripted_baseline else max_output_tokens,
        "native_tools": native_tools,
        "scripted_baseline": scripted_baseline,
        "wall_clock_seconds": elapsed,
        "jsonl_path": str(jsonl_path.name),
        "score": sim.score(),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run_many(
    *,
    model: str,
    runs: int,
    seed_base: int,
    days: int,
    max_steps: int,
    out_dir: str | Path,
    config_path: str | None = None,
    ollama_host: str = "http://localhost:11434",
    temperature: float = 0.2,
    num_ctx: int = 32768,
    max_output_tokens: int = 1024,
    native_tools: bool = False,
    scripted_baseline: bool = False,
) -> list[dict[str, Any]]:
    summaries = []
    for i in range(runs):
        summaries.append(
            run_one(
                model=model,
                seed=seed_base + i,
                days=days,
                max_steps=max_steps,
                out_dir=out_dir,
                config_path=config_path,
                ollama_host=ollama_host,
                temperature=temperature,
                num_ctx=num_ctx,
                max_output_tokens=max_output_tokens,
                native_tools=native_tools,
                scripted_baseline=scripted_baseline,
            )
        )
    return summaries


def build_report(results_dir: str | Path, out: str | Path | None = None) -> str:
    summaries = load_summaries(results_dir)
    if not summaries:
        report = "# Vending-Bench 2 Local Report\n\nNo `.summary.json` files found.\n"
        if out:
            Path(out).write_text(report, encoding="utf-8")
        return report
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for s in summaries:
        groups.setdefault((s["model"], int(s["days_requested"])), []).append(s)
    lines = [
        "# Vending-Bench 2 Local Report",
        "",
        "This report aggregates local reproduction-harness runs. The primary score is final bank balance.",
        "",
        "| Model | Days | Runs | Mean final balance | Stdev | Min | Max | Mean units sold | Completed runs | Mean invalid actions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    csv_rows = ["model,days,runs,mean_final_balance,stdev_final_balance,min_final_balance,max_final_balance,mean_units_sold,completed_runs,mean_invalid_actions"]
    for (model, days), rows in sorted(groups.items()):
        balances = [float(r["score"]["final_balance"]) for r in rows]
        units = [int(r["score"]["units_sold"]) for r in rows]
        invalids = [int(r["score"].get("invalid_actions", 0)) for r in rows]
        completed = sum(1 for r in rows if r["score"].get("terminated_reason") == "completed_full_horizon")
        stdev = statistics.stdev(balances) if len(balances) > 1 else 0.0
        line = (
            f"| `{model}` | {days} | {len(rows)} | ${statistics.mean(balances):,.2f} | ${stdev:,.2f} | "
            f"${min(balances):,.2f} | ${max(balances):,.2f} | {statistics.mean(units):,.1f} | {completed} | {statistics.mean(invalids):,.1f} |"
        )
        lines.append(line)
        csv_rows.append(
            f"{json.dumps(model)},{days},{len(rows)},{statistics.mean(balances):.2f},{stdev:.2f},{min(balances):.2f},{max(balances):.2f},{statistics.mean(units):.2f},{completed},{statistics.mean(invalids):.2f}"
        )
    lines.extend(
        [
            "",
            "## Reproducibility metadata",
            "",
            "| Run ID | Model | Seed | Config hash | Final balance | Net-worth diagnostic | Termination | Trace |",
            "|---|---|---:|---|---:|---:|---|---|",
        ]
    )
    for s in sorted(summaries, key=lambda x: x["run_id"]):
        score = s["score"]
        lines.append(
            f"| `{s['run_id']}` | `{s['model']}` | {s['seed']} | `{score['config_hash']}` | "
            f"${score['final_balance']:,.2f} | ${score['net_worth_diagnostic']:,.2f} | {score['terminated_reason']} | `{s['jsonl_path']}` |"
        )
    report = "\n".join(lines) + "\n"
    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        csv_path = out_path.with_suffix(".csv")
        csv_path.write_text("\n".join(csv_rows) + "\n", encoding="utf-8")
    return report


def load_summaries(results_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(results_dir)
    rows = []
    for f in sorted(path.glob("*.summary.json")):
        try:
            rows.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows


def safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in value)[:80]


def doctor(ollama_host: str = "http://localhost:11434", model: str | None = None) -> dict[str, Any]:
    client = OllamaClient(ollama_host)
    tags = client.tags()
    models = [m.get("name") for m in tags.get("models", [])]
    return {
        "ollama_host": ollama_host,
        "ollama_reachable": True,
        "models": models,
        "requested_model_present": (model in models) if model else None,
    }
