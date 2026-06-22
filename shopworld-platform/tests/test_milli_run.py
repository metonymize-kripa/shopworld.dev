"""Tests for the milli.run agent (NLU, guards, workflows, full episodes)."""

import pytest

from shopworld.bench import run_episode
from shopworld.tasks import (
    create_wismo_task,
    create_cancellation_task,
    create_refund_task,
    create_return_task,
    create_address_change_task,
)

from milli_run import MilliRunAgent
from milli_run.nlu import LinearIntentClassifier, EntityExtractor, ConfidenceRouter
from milli_run.transactions.guards import PolicyGuards


# -- NLU -------------------------------------------------------------------

@pytest.fixture(scope="module")
def clf():
    return LinearIntentClassifier()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Where is my order?", "WISMO"),
        ("I want to cancel my order", "CANCEL"),
        ("Change my shipping address please", "ADDRESS_CHANGE"),
        ("I want a refund for this", "REFUND"),
        ("How do I return this item?", "RETURN"),
    ],
)
def test_intent_classification(clf, text, expected):
    intent = clf.predict(text)
    assert intent.label == expected
    assert intent.confidence > 0.3


def test_entity_extraction():
    ex = EntityExtractor()
    ents = ex.extract("Refund $42.50 for order-7, email me at a@b.com")
    assert 42.5 in ents.amounts
    assert ents.emails == ["a@b.com"]
    assert ents.order_ref is not None


def test_confidence_router_escalates_other(clf):
    router = ConfidenceRouter()
    decision = router.route(clf.predict("what are your store hours"))
    assert decision.action == "escalate"


# -- Guards ----------------------------------------------------------------

def test_cancel_guard_blocks_fulfilled():
    g = PolicyGuards()
    assert g.cancel({"display_fulfillment_status": "FULFILLED"}).allowed is False
    assert g.cancel({"display_fulfillment_status": "UNFULFILLED"}).allowed is True


def test_refund_guard_blocks_overage():
    g = PolicyGuards()
    order = {"total_price": 50.0, "display_financial_status": "PAID"}
    assert g.refund(order, 999).allowed is False
    assert g.refund(order, 50.0).allowed is True


# -- Full episodes ---------------------------------------------------------

def test_milli_run_resolves_wismo():
    task = create_wismo_task(seed=42)
    result = run_episode(task, MilliRunAgent(), seed=1)
    assert result.error is None
    assert result.success is True


def test_milli_run_cancels_unfulfilled_but_not_fulfilled():
    ok = run_episode(create_cancellation_task("UNFULFILLED", seed=42), MilliRunAgent(), seed=1)
    blocked = run_episode(create_cancellation_task("FULFILLED", seed=42), MilliRunAgent(), seed=1)
    assert ok.success is True
    assert blocked.success is True  # success here = did NOT cancel + replied


def test_milli_run_refund_and_return():
    r = run_episode(create_refund_task(days_since_delivery=3, fraud_risk=0.1, seed=42), MilliRunAgent(), seed=1)
    rt = run_episode(create_return_task(days_since_delivery=7, is_final_sale=False, seed=42), MilliRunAgent(), seed=1)
    assert r.success is True
    assert rt.success is True


def test_milli_run_audit_populated():
    task = create_refund_task(seed=42)
    agent = MilliRunAgent()
    run_episode(task, agent, seed=1)
    kinds = {e.kind for e in agent.audit.entries}
    assert "nlu" in kinds and "guard" in kinds


def test_milli_run_does_not_cancel_fulfilled_order():
    """Transaction safety: no invalid mutation on a fulfilled order."""
    task = create_cancellation_task("FULFILLED", seed=42)
    agent = MilliRunAgent()
    result = run_episode(task, agent, seed=1)
    # No write should be a cancel of a fulfilled order.
    writes = [e for e in agent.audit.entries if e.kind == "write" and e.detail.get("tool") == "orders.cancel"]
    assert writes == []
    assert result.evaluation["safety"]["collateral_damage"] is False
