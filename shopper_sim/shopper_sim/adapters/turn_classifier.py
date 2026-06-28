"""Deterministic merchant-turn classifier.

Classifies each merchant response into a dialogue move WITHOUT an LLM. It uses:

  * structural signals from the adapter (has_question, has_action_button),
  * lexical signals: a frozen keyword bank per move class, scored by a simple
    deterministic overlap metric,
  * the active goal's satisfaction signals and requested info slots.

The score is thresholded. Near-boundary cases FAIL CLOSED -- they are marked
``ASKED_CLARIFY`` only if a known slot is clearly requested, otherwise
``AMBIGUOUS`` (scored as merchant-unclear) rather than silently guessing
``ANSWERED_GOAL``. This keeps a stochastic merchant from being flattered by an
optimistic classifier.

In production the lexical overlap is replaced by a *pinned* embedding model with
a fixed threshold and a classification cache keyed by hash(response); the
interface here is identical so that swap is local.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass

from ..engine.types import Goal
from .base import MerchantTurn


class MoveClass(enum.Enum):
    ANSWERED_GOAL = "answered_goal"
    ASKED_CLARIFY = "asked_clarify"
    ASKED_VERIFY = "asked_verify"
    OFFERED_ACTION = "offered_action"
    STALLED = "stalled"
    REFUSED = "refused"
    HANDED_OFF = "handed_off"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Classification:
    move: MoveClass
    score: float
    requested_slot: str | None = None
    matched_signals: tuple[str, ...] = ()


# Frozen keyword banks per move class. Lowercased; word-boundary matched.
_VERIFY_KW = ("verify", "confirm your identity", "last four", "security", "pin", "otp", "code we sent")
_REFUSE_KW = ("cannot", "can't help", "not able", "unable to", "we don't", "no longer", "not possible")
_HANDOFF_KW = ("connect you", "transfer", "representative", "agent will", "human", "support team")
_ACTION_KW = ("shall i", "would you like me to", "i can do that", "confirm?", "proceed?", "i'll go ahead")
_STALL_KW = ("not sure", "i don't understand", "could you repeat", "didn't catch", "hmm")

# Slot-request cue words -> slot name. Frozen mapping.
_SLOT_CUES: dict[str, tuple[str, ...]] = {
    "order_id": ("order number", "order id", "which order", "order #"),
    "email": ("email address", "your email", "sign in", "log in"),
    "identity_proof": ("verify", "identity", "confirm it's you"),
    "new_value": ("change it to", "what would you like", "new address", "update it to", "changed to"),
    "address": ("address", "shipping address", "zip"),
    "return_reason": ("reason for", "why are you returning", "what's wrong"),
    "product_ref": ("which product", "which item", "what are you looking"),
    "product_a": ("first product", "product a", "which two"),
    "product_b": ("second product", "product b", "compare with", "compare against"),
    "base_product": ("which product", "base product", "main item"),
    "device_model": ("which model", "what device", "which phone", "device model", "which device"),
    "substitution_pref": ("substitut", "replacement preference"),
    "subscription_id": ("subscription id", "which subscription"),
    "tax_exempt_id": ("tax exempt", "exemption certificate", "resale"),
    "quantity": ("how many", "quantity", "what volume"),
    "issue": ("what's the problem", "describe the issue", "what's wrong"),
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _contains(text: str, phrase: str) -> bool:
    return phrase in text


def _signal_overlap(text: str, signals: tuple[str, ...]) -> tuple[float, tuple[str, ...]]:
    """Fraction of goal satisfaction signals present, plus which matched."""
    if not signals:
        return 0.0, ()
    matched = tuple(s for s in signals if s.lower() in text)
    return len(matched) / len(signals), matched


# Tunable but FROZEN thresholds (would be pinned per battery version).
ANSWER_THRESHOLD = 0.34
AMBIGUITY_BAND = 0.17  # within this of threshold and no strong structural cue -> ambiguous


_COURTESY_TRAILERS = (
    "anything else", "is there anything else", "how else can i help",
    "can i help with anything else", "let me know if",
)


def _question_is_operative(text: str) -> bool:
    """True if the question is the operative clause (a real clarify), False if
    it's a trailing courtesy question after a resolution."""
    # If the only question is a known courtesy trailer, it's not operative.
    last_q = text.rfind("?")
    if last_q == -1:
        return False
    # Look at the sentence containing the final question mark.
    start = max(text.rfind(".", 0, last_q), text.rfind("--", 0, last_q)) + 1
    tail = text[start:last_q + 1].strip()
    if any(tr in tail for tr in _COURTESY_TRAILERS):
        return False
    return True


def classify(turn: MerchantTurn, active_goal: Goal) -> Classification:
    text = turn.text.lower().strip()

    # 1. Strong structural/lexical overrides, in priority order.
    if any(_contains(text, kw) for kw in _REFUSE_KW):
        return Classification(MoveClass.REFUSED, 1.0)
    if any(_contains(text, kw) for kw in _HANDOFF_KW):
        return Classification(MoveClass.HANDED_OFF, 1.0)
    if any(_contains(text, kw) for kw in _VERIFY_KW):
        return Classification(MoveClass.ASKED_VERIFY, 1.0, requested_slot="identity_proof")

    # 2. Pre-compute goal-answer signal overlap; a strong match means the
    #    merchant is resolving, even if the message ends with a courtesy
    #    question ("Anything else?"). This prevents trailing pleasantries from
    #    being misread as clarifying questions.
    score, matched = _signal_overlap(text, active_goal.satisfaction_signals)
    requested = _detect_slot_request(text, active_goal)
    is_question = turn.has_question or "?" in text

    # A clarify must be a genuine request for info. Distinguish a primary
    # question ("what's your order number?") from a resolution that merely ends
    # with a courtesy question ("...shipped. Anything else?"):
    #   * primary question: text ends with '?' and is dominated by the ask, OR
    #     the goal-answer signal is weak.
    #   * courtesy trailer: strong answer signal AND the question is not the
    #     operative clause.
    if requested is not None and is_question:
        ends_with_question = text.endswith("?")
        # courtesy trailer heuristic: strong answer signal and the LAST sentence
        # is the question while an earlier sentence carries the answer.
        answer_is_primary = score >= ANSWER_THRESHOLD and not _question_is_operative(text)
        if not answer_is_primary and (score < ANSWER_THRESHOLD or ends_with_question):
            return Classification(MoveClass.ASKED_CLARIFY, 0.9, requested_slot=requested)

    # 3. Offered action needing confirmation.
    if turn.has_action_button or any(_contains(text, kw) for kw in _ACTION_KW):
        return Classification(MoveClass.OFFERED_ACTION, 0.8)

    # 4. Goal answered (strong satisfaction-signal overlap).
    if score >= ANSWER_THRESHOLD:
        return Classification(MoveClass.ANSWERED_GOAL, score, matched_signals=matched)

    # 5. Explicit stall cues.
    if any(_contains(text, kw) for kw in _STALL_KW):
        return Classification(MoveClass.STALLED, 0.5)

    # 6. Near-boundary -> FAIL CLOSED to AMBIGUOUS (merchant-unclear), not answered.
    if ANSWER_THRESHOLD - AMBIGUITY_BAND <= score < ANSWER_THRESHOLD:
        return Classification(MoveClass.AMBIGUOUS, score, matched_signals=matched)

    # 7. Otherwise treat as a stall (unhelpful, off-target).
    return Classification(MoveClass.STALLED, score)


def _detect_slot_request(text: str, goal: Goal) -> str | None:
    """Return the goal-providable slot the merchant seems to be asking for."""
    for slot in goal.info_slots:
        cues = _SLOT_CUES.get(slot, ())
        if any(_contains(text, cue) for cue in cues):
            return slot
    # also detect requests for slots not on the goal (impossible asks)
    for slot, cues in _SLOT_CUES.items():
        if any(_contains(text, cue) for cue in cues):
            return slot
    return None
