"""Tests for the deterministic turn classifier, including fail-closed cases."""

from __future__ import annotations

from shopper_sim.adapters.base import MerchantTurn
from shopper_sim.adapters.turn_classifier import (
    ANSWER_THRESHOLD,
    MoveClass,
    classify,
)
from shopper_sim.engine.types import Goal


def _goal(**kw):
    base = dict(
        id="g",
        family_id="tracking",
        description="track order",
        preconditions=(),
        establishes=(),
        info_slots=("order_id",),
        satisfaction_signals=("shipped", "delivery", "tracking", "status"),
        params={},
    )
    base.update(kw)
    return Goal(**base)


def test_refusal_detected():
    c = classify(MerchantTurn(text="Sorry, we can't help with that."), _goal())
    assert c.move == MoveClass.REFUSED


def test_handoff_detected():
    c = classify(MerchantTurn(text="Let me connect you with a representative."), _goal())
    assert c.move == MoveClass.HANDED_OFF


def test_verify_detected():
    c = classify(MerchantTurn(text="Can you verify your identity first?"), _goal())
    assert c.move == MoveClass.ASKED_VERIFY


def test_clarify_with_slot_cue():
    c = classify(
        MerchantTurn(text="Sure -- what's your order number?", has_question=True),
        _goal(),
    )
    assert c.move == MoveClass.ASKED_CLARIFY
    assert c.requested_slot == "order_id"


def test_strong_answer_with_trailing_question_is_answer_not_clarify():
    """A clear resolution that ends with a courtesy question must not be read
    as a clarifying question."""
    c = classify(
        MerchantTurn(text="Your order is shipped and out for delivery. Anything else?"),
        _goal(),
    )
    assert c.move == MoveClass.ANSWERED_GOAL


def test_answer_above_threshold():
    c = classify(MerchantTurn(text="It has shipped; tracking shows delivery soon."), _goal())
    assert c.move == MoveClass.ANSWERED_GOAL
    assert c.score >= ANSWER_THRESHOLD


def test_stall_detected():
    c = classify(MerchantTurn(text="Hmm, I'm not sure I understand."), _goal())
    assert c.move == MoveClass.STALLED


def test_near_boundary_fails_closed_to_ambiguous():
    """A response that weakly matches one of several signals lands in the
    ambiguity band and is marked AMBIGUOUS, not ANSWERED_GOAL."""
    # Goal with four signals; matching exactly one => score 0.25, which sits in
    # [ANSWER_THRESHOLD - band, ANSWER_THRESHOLD).
    g = _goal(satisfaction_signals=("shipped", "delivery", "tracking", "status"))
    c = classify(MerchantTurn(text="Here is the delivery info you wanted."), g)
    assert c.move == MoveClass.AMBIGUOUS


def test_offered_action_detected():
    c = classify(
        MerchantTurn(text="I can do that for you. Shall I proceed?",
                     has_action_button=True),
        _goal(),
    )
    assert c.move == MoveClass.OFFERED_ACTION
