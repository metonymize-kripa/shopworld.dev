"""The deterministic dialogue-policy state machine.

This is the multistep core. Given a scenario's goal stack, a persona, a
factsheet, and a seed, it drives a conversation with a merchant adapter,
deciding the shopper's next move after every merchant turn -- with NO LLM.

Determinism: every *choice* (confirm vs decline, rephrase vs escalate, accept
handoff vs push back) is sampled from the seeded RNG, parameterised by persona
traits. The merchant may be stochastic; the shopper is not. Reproducibility of
the shopper is what makes scores comparable.

The precondition/establishes mechanism on goals is what *forces* real
multistep behaviour: a goal cannot be pursued until the journey state it
presupposes has been established by an earlier goal.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from ..engine.rng import DeterministicRNG
from ..engine.types import Factsheet, Goal, Persona, Scenario, Vertical
from ..nlg.realizer import realise
from ..persona.behavior import Decision, decide
from .base import MerchantAdapter, MerchantTurn
from .turn_classifier import Classification, MoveClass, classify


class PolicyState(enum.Enum):
    OPENING = "opening"
    AWAIT_MERCHANT = "await_merchant"
    POP_GOAL = "pop_goal"
    DONE = "done"
    FAILED = "failed"


class TurnOutcome(enum.Enum):
    GOAL_SATISFIED = "goal_satisfied"
    PROVIDED_SLOT = "provided_slot"
    DECLINED_SLOT = "declined_slot"  # impossible ask: shopper truthfully can't
    PROVIDED_VERIFY = "provided_verify"
    CONFIRMED_ACTION = "confirmed_action"
    DECLINED_ACTION = "declined_action"
    REPHRASED = "rephrased"
    ESCALATED = "escalated"
    ACCEPTED_HANDOFF = "accepted_handoff"
    ABANDONED = "abandoned"
    MERCHANT_REFUSED = "merchant_refused"
    MERCHANT_AMBIGUOUS = "merchant_ambiguous"
    LOOP_BROKEN = "loop_broken"
    PRECONDITION_UNMET = "precondition_unmet"


@dataclass
class DialogueTurn:
    """A full record of one shopper<->merchant exchange, for audit/scoring."""

    goal_id: str
    shopper_utterance: str
    merchant_text: str
    classification: MoveClass
    classification_score: float
    outcome: TurnOutcome
    requested_slot: str | None = None
    provided_value: str | None = None


@dataclass
class GoalResult:
    goal_id: str
    family_id: str
    satisfied: bool
    turns_used: int
    unnecessary_clarifies: int = 0
    impossible_asks: int = 0
    precondition_unmet: bool = False
    looped: bool = False
    outcome_terminal: TurnOutcome | None = None
    provided_slots: int = 0
    required_info: bool = False  # goal legitimately needed info from the shopper
    skipped_required_info: bool = False  # satisfied without ever gathering it


@dataclass
class DialogueTranscript:
    scenario_id: str
    persona_id: str
    seed: int
    turns: list[DialogueTurn] = field(default_factory=list)
    goal_results: list[GoalResult] = field(default_factory=list)
    journey_state: dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    total_turns: int = 0

    def goals_satisfied(self) -> int:
        return sum(1 for g in self.goal_results if g.satisfied)

    def to_dict(self) -> dict:
        """Full serialisation for audit/replay: every utterance, observation,
        classification, and goal result."""
        return {
            "scenario_id": self.scenario_id,
            "persona_id": self.persona_id,
            "seed": self.seed,
            "completed": self.completed,
            "total_turns": self.total_turns,
            "journey_state": dict(self.journey_state),
            "turns": [
                {
                    "goal_id": t.goal_id,
                    "shopper_utterance": t.shopper_utterance,
                    "merchant_text": t.merchant_text,
                    "classification": t.classification.value,
                    "classification_score": t.classification_score,
                    "outcome": t.outcome.value,
                    "requested_slot": t.requested_slot,
                    "provided_value": t.provided_value,
                }
                for t in self.turns
            ],
            "goal_results": [
                {
                    "goal_id": g.goal_id,
                    "family_id": g.family_id,
                    "satisfied": g.satisfied,
                    "turns_used": g.turns_used,
                    "unnecessary_clarifies": g.unnecessary_clarifies,
                    "impossible_asks": g.impossible_asks,
                    "precondition_unmet": g.precondition_unmet,
                    "looped": g.looped,
                    "provided_slots": g.provided_slots,
                    "required_info": g.required_info,
                    "skipped_required_info": g.skipped_required_info,
                    "outcome_terminal": g.outcome_terminal.value if g.outcome_terminal else None,
                }
                for g in self.goal_results
            ],
        }


@dataclass(frozen=True)
class PolicyConfig:
    global_turn_budget: int = 24
    per_goal_turn_budget: int = 6
    rephrase_budget: int = 2


class DialoguePolicy:
    """Drives a scenario's goal stack against a merchant adapter."""

    def __init__(
        self,
        scenario: Scenario,
        persona: Persona,
        adapter: MerchantAdapter,
        seed: int,
        config: PolicyConfig | None = None,
    ) -> None:
        self._scenario = scenario
        self._persona = persona
        self._adapter = adapter
        self._seed = seed
        self._config = config or PolicyConfig()
        self._rng = DeterministicRNG(seed).derive(
            f"policy:{scenario.scenario_id}:{persona.id}"
        )
        self._factsheet: Factsheet = scenario.factsheet
        self._state: dict[str, Any] = dict(scenario.initial_state)

    def run(self) -> DialogueTranscript:
        transcript = DialogueTranscript(
            scenario_id=self._scenario.scenario_id,
            persona_id=self._persona.id,
            seed=self._seed,
        )
        self._adapter.open_session(self._scenario.scenario_id, self._seed)
        try:
            self._run_goals(transcript)
        finally:
            self._adapter.close_session()
        transcript.journey_state = dict(self._state)
        transcript.completed = all(g.satisfied for g in transcript.goal_results)
        transcript.total_turns = len(transcript.turns)
        return transcript

    # -- goal loop ---------------------------------------------------------

    def _run_goals(self, transcript: DialogueTranscript) -> None:
        for goal in self._scenario.goals:
            if transcript.total_turns >= self._config.global_turn_budget:
                transcript.goal_results.append(
                    GoalResult(goal.id, goal.family_id, False, 0,
                               outcome_terminal=TurnOutcome.ABANDONED)
                )
                continue

            # Precondition check -- the structural enforcement of multistep.
            if not self._preconditions_met(goal):
                transcript.goal_results.append(
                    GoalResult(goal.id, goal.family_id, False, 0,
                               precondition_unmet=True,
                               outcome_terminal=TurnOutcome.PRECONDITION_UNMET)
                )
                continue

            result = self._pursue_goal(goal, transcript)
            transcript.goal_results.append(result)
            transcript.total_turns = len(transcript.turns)

            if result.satisfied:
                for key in goal.establishes:
                    self._state[key] = True
            else:
                # A failed prerequisite goal blocks dependents; keep recording
                # them as precondition_unmet on the next iterations.
                pass

    def _preconditions_met(self, goal: Goal) -> bool:
        return all(self._state.get(pc, False) for pc in goal.preconditions)

    # -- per-goal dialogue -------------------------------------------------

    def _pursue_goal(self, goal: Goal, transcript: DialogueTranscript) -> GoalResult:
        rephrases = 0
        unnecessary_clarifies = 0
        impossible_asks = 0
        provided_slots = 0
        last_pair: tuple[str, MoveClass] | None = None
        turns_used = 0

        # A goal "legitimately needs info" if it declares info slots that exist
        # in the factsheet (i.e. a competent merchant should ask for them).
        required_info = any(self._factsheet.has(s) for s in goal.info_slots)

        def result(satisfied: bool, terminal: TurnOutcome, looped: bool = False) -> GoalResult:
            skipped = bool(satisfied and required_info and provided_slots == 0)
            return GoalResult(
                goal_id=goal.id,
                family_id=goal.family_id,
                satisfied=satisfied,
                turns_used=turns_used,
                unnecessary_clarifies=unnecessary_clarifies,
                impossible_asks=impossible_asks,
                looped=looped,
                outcome_terminal=terminal,
                provided_slots=provided_slots,
                required_info=required_info,
                skipped_required_info=skipped,
            )

        utterance = self._open_utterance(goal)

        for _ in range(self._config.per_goal_turn_budget):
            if transcript.total_turns + turns_used >= self._config.global_turn_budget:
                return result(False, TurnOutcome.ABANDONED)

            merchant = self._adapter.send(utterance)
            cls = classify(merchant, goal)
            turns_used += 1

            # Loop detection: same utterance + same merchant move twice.
            pair = (utterance, cls.move)
            if last_pair is not None and pair == last_pair:
                transcript.turns.append(
                    DialogueTurn(goal.id, utterance, merchant.text, cls.move,
                                 cls.score, TurnOutcome.LOOP_BROKEN)
                )
                return result(False, TurnOutcome.LOOP_BROKEN, looped=True)
            last_pair = pair

            outcome, next_utterance, info = self._handle_move(goal, cls, merchant)

            transcript.turns.append(
                DialogueTurn(
                    goal_id=goal.id,
                    shopper_utterance=utterance,
                    merchant_text=merchant.text,
                    classification=cls.move,
                    classification_score=cls.score,
                    outcome=outcome,
                    requested_slot=cls.requested_slot,
                    provided_value=info,
                )
            )

            if outcome == TurnOutcome.PROVIDED_SLOT:
                provided_slots += 1
                if cls.requested_slot not in goal.info_slots:
                    unnecessary_clarifies += 1
            if outcome == TurnOutcome.PROVIDED_VERIFY:
                provided_slots += 1
            if outcome == TurnOutcome.DECLINED_SLOT:
                impossible_asks += 1

            if outcome == TurnOutcome.GOAL_SATISFIED:
                return result(True, outcome)
            if outcome in (TurnOutcome.ABANDONED, TurnOutcome.MERCHANT_REFUSED):
                return result(False, outcome)
            if outcome in (TurnOutcome.ESCALATED, TurnOutcome.ACCEPTED_HANDOFF):
                # Escalation/handoff is a degraded resolution path: not bot-
                # satisfied, recorded as terminal.
                return result(False, outcome)
            if outcome == TurnOutcome.REPHRASED:
                rephrases += 1
                if rephrases > self._config.rephrase_budget:
                    d = decide("stall_response", self._persona, self._rng)
                    if d == Decision.ESCALATE:
                        utterance = self._escalate_utterance(goal)
                        continue
                    return result(False, TurnOutcome.ABANDONED)

            utterance = next_utterance

        # Per-goal budget exhausted without satisfaction.
        return result(False, TurnOutcome.ABANDONED)

    # -- move handling -----------------------------------------------------

    def _handle_move(
        self, goal: Goal, cls: Classification, merchant: MerchantTurn
    ) -> tuple[TurnOutcome, str, str | None]:
        move = cls.move

        if move == MoveClass.ANSWERED_GOAL:
            return TurnOutcome.GOAL_SATISFIED, "", None

        if move == MoveClass.ASKED_CLARIFY:
            slot = cls.requested_slot
            if slot is not None and self._factsheet.has(slot):
                value = str(self._factsheet.get(slot))
                return TurnOutcome.PROVIDED_SLOT, self._slot_answer(slot, value), value
            # Impossible ask: shopper truthfully cannot provide it.
            return TurnOutcome.DECLINED_SLOT, self._decline_slot_utterance(slot), None

        if move == MoveClass.ASKED_VERIFY:
            if self._factsheet.has("identity_proof"):
                value = str(self._factsheet.get("identity_proof"))
                return TurnOutcome.PROVIDED_VERIFY, self._slot_answer("identity_proof", value), value
            return TurnOutcome.DECLINED_SLOT, self._decline_slot_utterance("identity_proof"), None

        if move == MoveClass.OFFERED_ACTION:
            d = decide("confirm_action", self._persona, self._rng)
            if d == Decision.ACCEPT:
                return TurnOutcome.CONFIRMED_ACTION, self._confirm_utterance(), None
            return TurnOutcome.DECLINED_ACTION, self._decline_action_utterance(), None

        if move == MoveClass.REFUSED:
            return TurnOutcome.MERCHANT_REFUSED, "", None

        if move == MoveClass.HANDED_OFF:
            # accept handoff unless persona is very impatient
            if self._persona.patience < 0.25 and self._rng.bernoulli(0.5):
                return TurnOutcome.ABANDONED, "", None
            return TurnOutcome.ACCEPTED_HANDOFF, "", None

        if move == MoveClass.AMBIGUOUS:
            # merchant-unclear: shopper presses for detail (rephrase-style)
            return TurnOutcome.MERCHANT_AMBIGUOUS, self._press_detail_utterance(goal), None

        # STALLED (default)
        return TurnOutcome.REPHRASED, self._rephrase_utterance(goal), None

    # -- utterance generation (all via the deterministic realiser) ---------

    def _vertical(self) -> Vertical:
        return self._scenario.vertical

    def _open_utterance(self, goal: Goal) -> str:
        slots = dict(goal.params)
        u = realise(goal.family_id, slots, self._persona, self._vertical(),
                    self._rng.derive(f"open:{goal.id}"))
        return u.text

    def _rephrase_utterance(self, goal: Goal) -> str:
        # pull a *different* phrasing of the same goal (seeded by attempt salt)
        slots = dict(goal.params)
        u = realise(goal.family_id, slots, self._persona, self._vertical(),
                    self._rng.derive(f"rephrase:{goal.id}:{self._rng.randint(0, 1_000_000)}"))
        return u.text

    def _press_detail_utterance(self, goal: Goal) -> str:
        return f"Sorry, I didn't follow -- can you be specific about {goal.description.lower()}"

    def _escalate_utterance(self, goal: Goal) -> str:
        u = realise("support_escalation", {"issue": goal.description},
                    self._persona, self._vertical(),
                    self._rng.derive(f"escalate:{goal.id}"))
        return u.text

    def _slot_answer(self, slot: str, value: str) -> str:
        readable = slot.replace("_", " ")
        if self._persona.tech_fluency < 0.4:
            return value
        return f"{readable}: {value}"

    def _decline_slot_utterance(self, slot: str | None) -> str:
        what = (slot or "that").replace("_", " ")
        return f"I don't have {what} -- I was never given it."

    def _confirm_utterance(self) -> str:
        return "Yes, please go ahead."

    def _decline_action_utterance(self) -> str:
        return "No, hold off for now."
