"""Tests for the LLM tool-use agent (offline scripted client)."""

from shopworld.bench import run_episode
from shopworld.tasks import (
    create_wismo_task,
    create_cancellation_task,
    create_refund_task,
    create_return_task,
)

from llm_agent import LLMAgent, ScriptedLLMClient
from llm_agent.react_loop import parse_action, build_user_message


def test_parse_action_extracts_json():
    assert parse_action('{"tool": "orders.query", "args": {"id": "x"}}') == {
        "tool": "orders.query",
        "args": {"id": "x"},
    }
    assert parse_action("here you go {\"tool\": \"tickets.reply\", \"args\": {}}")["tool"] == "tickets.reply"
    assert parse_action("no json here") is None


def test_build_user_message_has_context_block():
    msg = build_user_message({"id": "t1", "subject": "Cancel my order", "order_id": "o1"}, None, [])
    assert "<CONTEXT>" in msg and "t1" in msg


def test_llm_agent_resolves_wismo():
    result = run_episode(create_wismo_task(seed=42), LLMAgent(), seed=1)
    assert result.error is None
    assert result.success is True


def test_llm_agent_handles_cancellation_both_states():
    ok = run_episode(create_cancellation_task("UNFULFILLED", seed=42), LLMAgent(), seed=1)
    blocked = run_episode(create_cancellation_task("FULFILLED", seed=42), LLMAgent(), seed=1)
    assert ok.success is True
    assert blocked.success is True


def test_llm_agent_refund_and_return():
    r = run_episode(create_refund_task(days_since_delivery=3, seed=42), LLMAgent(), seed=1)
    rt = run_episode(create_return_task(days_since_delivery=7, seed=42), LLMAgent(), seed=1)
    assert r.success is True
    assert rt.success is True


def test_scripted_client_is_deterministic():
    client = ScriptedLLMClient()
    msgs = [{"role": "user", "content": '<CONTEXT>{"ticket_id":"t","order_id":"o","subject":"I want a refund","order":{"total_price":10.0,"display_financial_status":"PAID"},"history":[]}</CONTEXT>'}]
    assert client.complete(msgs) == client.complete(msgs)
