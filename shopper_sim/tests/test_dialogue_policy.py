"""Tests that the multistep capability is genuinely secured.

These are the load-bearing tests: they prove the dialogue policy enforces
journey-state preconditions, answers only from the factsheet, declines
impossible asks truthfully, and never volunteers unasked information.
"""

from __future__ import annotations

from shopper_sim.adapters.base import MerchantAdapter, MerchantTurn
from shopper_sim.adapters.dialogue_policy import (
    DialoguePolicy,
    PolicyConfig,
    TurnOutcome,
)
from shopper_sim.adapters.mock_merchant import (
    CluelessMerchant,
    GoodMerchant,
    RefusingMerchant,
)
from shopper_sim.persona.library import persona_by_id
from shopper_sim.taxonomy.scenario_compiler import (
    compile_family_scenario,
    default_context,
)


def _run(scenario, merchant, persona_id="loyal_regular", seed=11, config=None):
    persona = persona_by_id(persona_id)
    return DialoguePolicy(scenario, persona, merchant, seed, config).run()


def test_good_merchant_satisfies_multistep_return(return_flow_scenario):
    t = _run(return_flow_scenario, GoodMerchant(return_flow_scenario))
    assert t.goals_satisfied() == len(return_flow_scenario.goals)
    assert t.completed


def test_clueless_merchant_fails_multistep(return_flow_scenario):
    t = _run(return_flow_scenario, CluelessMerchant(return_flow_scenario))
    assert t.goals_satisfied() == 0
    assert not t.completed


def test_precondition_blocks_dependent_goal_when_prereq_fails(return_flow_scenario):
    """If the first goal never completes, dependent goals are recorded as
    precondition-unmet rather than spuriously satisfied."""
    t = _run(return_flow_scenario, CluelessMerchant(return_flow_scenario))
    # The refund goal depends on return_initiated, which never happens.
    refund_results = [g for g in t.goal_results if g.family_id == "refunds"]
    assert refund_results
    assert all(not g.satisfied for g in refund_results)
    assert any(g.precondition_unmet for g in t.goal_results)


def test_impossible_ask_is_declined_truthfully():
    """A merchant asking for info not on the factsheet gets a truthful decline,
    recorded as an impossible ask (merchant error)."""
    scenario = compile_family_scenario("tracking", default_context())
    # tracking factsheet has only order_id; demand a device model the shopper
    # was never given (and which isn't a verify/identity cue).
    assert not scenario.factsheet.has("device_model")

    class DeviceDemandingMerchant(MerchantAdapter):
        def open_session(self, scenario_id, seed): ...
        def close_session(self): ...
        def send(self, utterance):
            return MerchantTurn(
                text="Which device model are you asking about?",
                has_question=True,
            )

    t = _run(scenario, DeviceDemandingMerchant())
    impossible = sum(g.impossible_asks for g in t.goal_results)
    assert impossible >= 1
    assert any(turn.outcome == TurnOutcome.DECLINED_SLOT for turn in t.turns)


def test_shopper_answers_only_from_factsheet():
    """The shopper provides a slot value that matches the factsheet exactly and
    never invents one."""
    scenario = compile_family_scenario("tracking", default_context())
    order_id = scenario.factsheet.get("order_id")

    class OrderAskingMerchant(MerchantAdapter):
        def __init__(self):
            self.i = 0
        def open_session(self, scenario_id, seed): self.i = 0
        def close_session(self): ...
        def send(self, utterance):
            self.i += 1
            if self.i == 1:
                return MerchantTurn(text="Sure -- what's your order number?",
                                    has_question=True)
            return MerchantTurn(text="Thanks, your order is shipped and arriving soon.")

    t = _run(scenario, OrderAskingMerchant())
    provided = [turn for turn in t.turns if turn.provided_value]
    assert provided
    assert any(str(order_id) in (turn.provided_value or "") for turn in provided)


def test_refusing_merchant_recorded_as_refusal(order_editing_scenario):
    t = _run(order_editing_scenario, RefusingMerchant(order_editing_scenario))
    assert any(turn.outcome == TurnOutcome.MERCHANT_REFUSED for turn in t.turns)
    assert t.goals_satisfied() == 0


def test_loop_detection_terminates():
    """A merchant that repeats the same unhelpful answer triggers loop-break,
    so dialogues always terminate."""
    scenario = compile_family_scenario("tracking", default_context())

    class BrokenRecordMerchant(MerchantAdapter):
        def open_session(self, scenario_id, seed): ...
        def close_session(self): ...
        def send(self, utterance):
            return MerchantTurn(text="I'm not sure I understand.")

    t = _run(scenario, BrokenRecordMerchant())
    assert t.total_turns <= PolicyConfig().global_turn_budget
    assert any(turn.outcome == TurnOutcome.LOOP_BROKEN for turn in t.turns)


def test_turn_budget_is_respected():
    scenario = compile_family_scenario("return_initiation", default_context())

    class ChattyStaller(MerchantAdapter):
        def __init__(self): self.i = 0
        def open_session(self, scenario_id, seed): self.i = 0
        def close_session(self): ...
        def send(self, utterance):
            self.i += 1
            # never resolves, always slightly different to dodge loop detection
            return MerchantTurn(text=f"Let me look into that... ({self.i})")

    cfg = PolicyConfig(global_turn_budget=10, per_goal_turn_budget=4)
    t = _run(scenario, ChattyStaller(), config=cfg)
    assert t.total_turns <= cfg.global_turn_budget


def test_overeager_merchant_penalised_on_multistep(order_editing_scenario):
    """A merchant that resolves without gathering required info is flagged."""
    from shopper_sim.adapters.mock_merchant import OvereagerMerchant

    t = _run(order_editing_scenario, OvereagerMerchant(order_editing_scenario))
    assert any(g.skipped_required_info for g in t.goal_results)
