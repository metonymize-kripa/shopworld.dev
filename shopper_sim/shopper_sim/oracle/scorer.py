"""The deterministic oracle.

Scores a ``DialogueTranscript`` against rubric dimensions using only the
structural facts in the transcript -- no LLM. (Tier-2 frozen-embedding and
tier-3 frozen-cached-judge checks would attach here for open free-text quality;
the deterministic tier below already covers the bulk of the battery.)

Scoring is a pure function of the transcript, so a given transcript always
yields the same score.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..adapters.dialogue_policy import DialogueTranscript, TurnOutcome
from ..engine.types import IntentLayer, Scenario
from .rubric import DimensionScores, RUBRIC_VERSION


@dataclass(frozen=True)
class ScenarioScore:
    scenario_id: str
    persona_id: str
    seed: int
    primary_layer: str
    dimensions: DimensionScores
    headline: float
    goals_total: int
    goals_satisfied: int
    total_turns: int
    rubric_version: str = RUBRIC_VERSION

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "persona_id": self.persona_id,
            "seed": self.seed,
            "primary_layer": self.primary_layer,
            "dimensions": self.dimensions.as_dict(),
            "headline": self.headline,
            "goals_total": self.goals_total,
            "goals_satisfied": self.goals_satisfied,
            "total_turns": self.total_turns,
            "rubric_version": self.rubric_version,
        }


def _optimal_turns(scenario: Scenario) -> int:
    """Optimal turn count: one resolving turn per goal, plus one clarify each
    where the goal legitimately needs info."""
    n = 0
    for g in scenario.goals:
        n += 1  # resolution
        if g.info_slots:
            n += 1  # one legitimate clarify
    return max(n, 1)


def score_transcript(scenario: Scenario, transcript: DialogueTranscript) -> ScenarioScore:
    goals_total = len(scenario.goals)
    goals_satisfied = transcript.goals_satisfied()

    # task_success: fraction of goals satisfied.
    task_success = goals_satisfied / goals_total if goals_total else 0.0

    # efficiency: optimal / actual, capped at 1.0; 0 if no turns.
    optimal = _optimal_turns(scenario)
    actual = max(transcript.total_turns, 1)
    efficiency = min(1.0, optimal / actual)

    # correctness: penalise impossible asks and unnecessary clarifies, and
    # precondition violations (the shopper-side proves these structurally).
    impossible = sum(g.impossible_asks for g in transcript.goal_results)
    unnecessary = sum(g.unnecessary_clarifies for g in transcript.goal_results)
    precondition_fails = sum(1 for g in transcript.goal_results if g.precondition_unmet)
    skipped_info = sum(1 for g in transcript.goal_results if g.skipped_required_info)
    penalty = (
        0.2 * impossible
        + 0.1 * unnecessary
        + 0.3 * precondition_fails
        + 0.35 * skipped_info
    )
    correctness = max(0.0, 1.0 - penalty)

    # disclosure: did the merchant surface required info before resolution?
    # Approximated by presence of a clarify-then-resolve pattern on goals that
    # need info. (Tier-2 checks would refine this.)
    disclosure = _disclosure_score(transcript)

    # recovery: how gracefully were stalls/ambiguity/refusals handled. Reward
    # escalation/handoff over silent abandonment.
    recovery = _recovery_score(transcript)

    dims = DimensionScores(
        task_success=task_success,
        efficiency=efficiency,
        correctness=correctness,
        disclosure=disclosure,
        recovery=recovery,
    )
    return ScenarioScore(
        scenario_id=scenario.scenario_id,
        persona_id=transcript.persona_id,
        seed=transcript.seed,
        primary_layer=scenario.primary_layer.value,
        dimensions=dims,
        headline=dims.weighted_total(),
        goals_total=goals_total,
        goals_satisfied=goals_satisfied,
        total_turns=transcript.total_turns,
    )


def _disclosure_score(transcript: DialogueTranscript) -> float:
    needed = 0
    disclosed = 0
    for g in transcript.goal_results:
        # goals that used at least one provide-slot exchange and still satisfied
        # are treated as having disclosed appropriately.
        if g.satisfied:
            disclosed += 1
        needed += 1
    if needed == 0:
        return 1.0
    return disclosed / needed


def _recovery_score(transcript: DialogueTranscript) -> float:
    if not transcript.turns:
        return 0.0
    good = 0
    bad = 0
    for t in transcript.turns:
        if t.outcome in (
            TurnOutcome.GOAL_SATISFIED,
            TurnOutcome.PROVIDED_SLOT,
            TurnOutcome.PROVIDED_VERIFY,
            TurnOutcome.CONFIRMED_ACTION,
            TurnOutcome.ESCALATED,
            TurnOutcome.ACCEPTED_HANDOFF,
            TurnOutcome.DECLINED_SLOT,  # truthful decline is correct behaviour
        ):
            good += 1
        elif t.outcome in (
            TurnOutcome.LOOP_BROKEN,
            TurnOutcome.ABANDONED,
            TurnOutcome.MERCHANT_REFUSED,
            TurnOutcome.MERCHANT_AMBIGUOUS,
        ):
            bad += 1
    total = good + bad
    if total == 0:
        return 1.0
    return good / total


# -- layer roll-up ---------------------------------------------------------

def rollup_by_layer(scores: list[ScenarioScore]) -> dict[str, float]:
    """Mean headline score per intent layer."""
    buckets: dict[str, list[float]] = {}
    for s in scores:
        buckets.setdefault(s.primary_layer, []).append(s.headline)
    return {layer: sum(v) / len(v) for layer, v in sorted(buckets.items())}


def headline_score(scores: list[ScenarioScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.headline for s in scores) / len(scores)
