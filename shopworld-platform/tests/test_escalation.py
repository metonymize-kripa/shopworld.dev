"""Escalation scenarios: milli.run escalates threats; the LLM agent does not."""

import pytest

from shopworld.bench import run_episode
from shopworld.tasks import create_escalation_task

from milli_run import MilliRunAgent
from llm_agent import LLMAgent


@pytest.mark.parametrize("variant", ["legal_threat", "chargeback_threat", "fraud_accusation"])
def test_milli_run_escalates(variant):
    result = run_episode(create_escalation_task(variant=variant, seed=42), MilliRunAgent(), seed=1)
    assert result.success is True
    assert result.evaluation["task"]["success"] is True


@pytest.mark.parametrize("variant", ["legal_threat", "chargeback_threat", "fraud_accusation"])
def test_llm_agent_misses_escalation(variant):
    result = run_episode(create_escalation_task(variant=variant, seed=42), LLMAgent(), seed=1)
    # The scripted LLM has no policy/escalation reasoning -> fails to escalate.
    assert result.success is False


def test_milli_run_does_not_refund_abuser():
    """No policy drift: milli.run must not refund an abusive/fraud-risk customer."""
    agent = MilliRunAgent()
    result = run_episode(create_escalation_task(variant="chargeback_threat", seed=42), agent, seed=1)
    assert result.evaluation["business"]["refund_leakage"] == 0.0
    refunds_created = [
        e for e in agent.audit.entries if e.kind == "write" and e.detail.get("tool") == "refunds.create"
    ]
    assert refunds_created == []
