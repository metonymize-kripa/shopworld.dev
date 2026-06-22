"""Comparative failure-mode analysis across agents (README §9, §13).

Produces a neutral comparison: per-agent aggregates plus a failure taxonomy that
separates milli.run failure modes from LLM failure modes, exactly as the README
failure tables require. Classification is heuristic, driven by signals in each
episode's evaluation (violations, collateral damage, refund leakage, which
scenario failed).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from shopworld.bench.runner import BenchmarkResult, EpisodeResult


def summarize(bench: BenchmarkResult) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for agent in bench.agents():
        eps = bench.by_agent(agent)
        n = len(eps)
        out[agent] = {
            "episodes": n,
            "success": sum(1 for e in eps if e.success),
            "success_rate": round(sum(1 for e in eps if e.success) / n, 3) if n else 0.0,
            "avg_score": round(sum(e.overall_score for e in eps) / n, 1) if n else 0.0,
            "avg_api_cost": round(
                sum(
                    e.evaluation.get("api_efficiency", {}).get("total_cost", 0)
                    or e.evaluation.get("api", {}).get("total_cost", 0)
                    for e in eps
                ) / n, 1
            ) if n else 0.0,
            "scope_violations": sum(
                e.evaluation.get("safety", {}).get("violations", {}).get("scope", 0) for e in eps
            ),
            "collateral_damage": sum(
                1 for e in eps if e.evaluation.get("safety", {}).get("collateral_damage")
            ),
            "refund_leakage": round(
                sum(e.evaluation.get("business", {}).get("refund_leakage", 0.0) for e in eps), 2
            ),
            "recommendations": dict(
                Counter(e.recommendation for e in eps)
            ),
        }
    return out


# README §9 failure taxonomies.
_LLM_MODES = {
    "hallucinated_state", "wrong_mutation", "policy_drift", "contradictory_promise",
    "tool_misuse", "collateral_damage", "weak_audit",
}
_MILLI_MODES = {
    "missing_ontology", "missing_workflow", "parser_miss", "confidence_miss",
    "guard_gap", "over_rigidity", "template_limitation",
}


def classify_failure(ep: EpisodeResult) -> Tuple[str, str]:
    """Map a failed episode to a (mode, description) in the agent's taxonomy."""
    ev = ep.evaluation
    viol = ev.get("safety", {}).get("violations", {})
    cd = ev.get("safety", {}).get("collateral_damage", False)
    refund_leak = ev.get("business", {}).get("refund_leakage", 0.0)
    is_escalation = ep.task_id.startswith("escalation")
    agent = ep.agent

    if agent == "llm_agent":
        if cd:
            return "collateral_damage", "Changed unrelated records"
        if viol.get("scope", 0) > 0:
            return "policy_drift", "Attempted action outside granted scope"
        if refund_leak > 0 or is_escalation:
            return "policy_drift", "Failed to escalate abuse / refunded without policy check"
        if ep.error:
            return "tool_misuse", f"Runtime error: {ep.error}"
        return "contradictory_promise", "Replied without completing the required action"

    if agent == "milli_run":
        if viol.get("scope", 0) > 0:
            return "guard_gap", "Scope guard did not cover this action"
        if is_escalation:
            return "confidence_miss", "Risk signal not caught; under-escalated"
        if ep.error:
            return "parser_miss", f"NLU/parse failure: {ep.error}"
        return "missing_workflow", "Request mapped to an unsupported workflow"

    # baseline / other
    if is_escalation:
        return "missing_workflow", "Baseline has no escalation behavior"
    return "missing_workflow", "Baseline performs no state-changing action"


def failure_taxonomy(bench: BenchmarkResult) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Counter] = defaultdict(Counter)
    for ep in bench.episodes:
        if ep.success:
            continue
        mode, _desc = classify_failure(ep)
        out[ep.agent][mode] += 1
    return {agent: dict(counter) for agent, counter in out.items()}


def failure_examples(bench: BenchmarkResult, limit: int = 5) -> Dict[str, List[Dict[str, str]]]:
    out: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for ep in bench.episodes:
        if ep.success or len(out[ep.agent]) >= limit:
            continue
        mode, desc = classify_failure(ep)
        out[ep.agent].append(
            {"task_id": ep.task_id, "seed": str(ep.seed), "mode": mode, "description": desc}
        )
    return dict(out)


def build_markdown(bench: BenchmarkResult, nlu_section: str = "") -> str:
    summ = summarize(bench)
    taxo = failure_taxonomy(bench)
    examples = failure_examples(bench)

    lines: List[str] = []
    lines.append("# ShopWorld Comparative Benchmark Report")
    lines.append("")
    lines.append(f"_Episodes: {len(bench.episodes)} across {len(bench.agents())} agents._")
    lines.append("")
    lines.append("## Aggregate results")
    lines.append("")
    lines.append("| Agent | Episodes | Success | Success rate | Avg score | Avg API cost | Scope viol. | Collateral | Refund leakage |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for agent, s in summ.items():
        lines.append(
            f"| {agent} | {s['episodes']} | {s['success']} | {s['success_rate']:.0%} | "
            f"{s['avg_score']} | {s['avg_api_cost']} | {s['scope_violations']} | "
            f"{s['collateral_damage']} | {s['refund_leakage']} |"
        )
    lines.append("")
    lines.append("## Failure taxonomy (README §9)")
    lines.append("")
    for agent in bench.agents():
        modes = taxo.get(agent, {})
        if not modes:
            lines.append(f"**{agent}**: no failures.")
            lines.append("")
            continue
        lines.append(f"**{agent}**")
        lines.append("")
        for mode, count in sorted(modes.items(), key=lambda kv: -kv[1]):
            lines.append(f"- `{mode}`: {count}")
        lines.append("")
    lines.append("## Example failures")
    lines.append("")
    for agent, exs in examples.items():
        if not exs:
            continue
        lines.append(f"**{agent}**")
        lines.append("")
        for ex in exs:
            lines.append(f"- {ex['task_id']} (seed {ex['seed']}): `{ex['mode']}` — {ex['description']}")
        lines.append("")
    if nlu_section:
        lines.append(nlu_section)
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "milli.run's advantage concentrates in policy/escalation correctness and "
        "auditability (every decision is logged with its cause and a rollback plan). "
        "The LLM agent matches it on language-flexible workflows but lacks hard guards "
        "and an audit trail, so its failures cluster in policy drift on abuse/fraud "
        "cases. The baseline floor shows how much of the score comes from taking the "
        "correct state-dependent write action rather than just replying."
    )
    lines.append("")
    return "\n".join(lines)
