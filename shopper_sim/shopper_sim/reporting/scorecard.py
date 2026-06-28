"""Reporting and hill-climb support.

Turns a ``RunResult`` into a human-readable scorecard, and diffs two runs on
the IDENTICAL frozen battery to surface regressions and improvements across
generations of a merchant's AI -- the hill-climb loop the product is sold on.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..orchestrator.runner import RunResult


def format_scorecard(run: RunResult) -> str:
    lines: list[str] = []
    lines.append(f"Battery: {run.battery_version}")
    lines.append(f"Root hash: {run.manifest['root_hash']}")
    lines.append(f"Headline score: {run.headline * 100:.1f} / 100")
    lines.append("")
    lines.append("By intent layer:")
    for layer, score in run.layer_scores.items():
        lines.append(f"  {layer:<14} {score * 100:5.1f}")
    lines.append("")
    lines.append("Worst-performing scenarios:")
    multi_persona = len({d.persona_id for d in run.distributions}) > 1
    worst = sorted(run.distributions, key=lambda d: d.mean_headline())[:8]
    for d in worst:
        flag = "  (inconsistent)" if d.stdev_headline() > 0.15 else ""
        label = f"{d.title} / {d.persona_id}" if multi_persona else d.title
        lines.append(
            f"  {d.mean_headline() * 100:5.1f}  {label:<46} "
            f"[{d.primary_layer}] sd={d.stdev_headline():.2f}{flag}"
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class ScenarioDelta:
    scenario_id: str
    title: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before


@dataclass(frozen=True)
class GenerationDiff:
    headline_before: float
    headline_after: float
    regressions: tuple[ScenarioDelta, ...]
    improvements: tuple[ScenarioDelta, ...]
    same_battery: bool

    @property
    def headline_delta(self) -> float:
        return self.headline_after - self.headline_before


def diff_runs(before: RunResult, after: RunResult, threshold: float = 0.02) -> GenerationDiff:
    """Compare two runs. Only meaningful if they share a battery root hash."""
    same_battery = before.manifest["root_hash"] == after.manifest["root_hash"]

    before_by_id = {(d.scenario_id, d.persona_id): d for d in before.distributions}
    after_by_id = {(d.scenario_id, d.persona_id): d for d in after.distributions}
    multi_persona = len({d.persona_id for d in after.distributions}) > 1

    deltas: list[ScenarioDelta] = []
    for key, a in after_by_id.items():
        b = before_by_id.get(key)
        if b is None:
            continue
        label = f"{a.title} / {a.persona_id}" if multi_persona else a.title
        deltas.append(
            ScenarioDelta(a.scenario_id, label, b.mean_headline(), a.mean_headline())
        )

    regressions = tuple(
        sorted((d for d in deltas if d.delta < -threshold), key=lambda d: d.delta)
    )
    improvements = tuple(
        sorted((d for d in deltas if d.delta > threshold), key=lambda d: -d.delta)
    )
    return GenerationDiff(
        headline_before=before.headline,
        headline_after=after.headline,
        regressions=regressions,
        improvements=improvements,
        same_battery=same_battery,
    )


def format_diff(diff: GenerationDiff) -> str:
    lines: list[str] = []
    if not diff.same_battery:
        lines.append("WARNING: runs used different batteries; scores are not comparable.")
        lines.append("")
    arrow = "+" if diff.headline_delta >= 0 else ""
    lines.append(
        f"Headline: {diff.headline_before * 100:.1f} -> {diff.headline_after * 100:.1f} "
        f"({arrow}{diff.headline_delta * 100:.1f})"
    )
    lines.append("")
    if diff.regressions:
        lines.append(f"Regressions ({len(diff.regressions)}):")
        for d in diff.regressions[:10]:
            lines.append(f"  {d.delta * 100:+5.1f}  {d.title}")
    else:
        lines.append("No regressions.")
    lines.append("")
    if diff.improvements:
        lines.append(f"Improvements ({len(diff.improvements)}):")
        for d in diff.improvements[:10]:
            lines.append(f"  {d.delta * 100:+5.1f}  {d.title}")
    else:
        lines.append("No improvements.")
    return "\n".join(lines)
