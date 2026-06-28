"""Determinism property tests for full simulator runs.

The shopper side must be a pure function of (scenario, persona, seed). Same
inputs -> byte-identical transcripts and scores. This is what makes the battery
a stable, comparable ruler.
"""

from __future__ import annotations

import json

from shopper_sim.adapters.dialogue_policy import DialoguePolicy
from shopper_sim.adapters.mock_merchant import GoodMerchant
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas, persona_by_id
from shopper_sim.oracle.scorer import score_transcript
from shopper_sim.taxonomy.scenario_compiler import (
    compile_family_scenario,
    compile_full_battery,
    default_context,
)


def _transcript_digest(t):
    return json.dumps(
        [
            {
                "goal": turn.goal_id,
                "u": turn.shopper_utterance,
                "m": turn.merchant_text,
                "cls": turn.classification.value,
                "out": turn.outcome.value,
            }
            for turn in t.turns
        ],
        sort_keys=True,
    )


def test_same_seed_identical_transcript():
    scenario = compile_family_scenario("return_initiation", default_context())
    persona = persona_by_id("loyal_regular")
    t1 = DialoguePolicy(scenario, persona, GoodMerchant(scenario), seed=42).run()
    t2 = DialoguePolicy(scenario, persona, GoodMerchant(scenario), seed=42).run()
    assert _transcript_digest(t1) == _transcript_digest(t2)


def test_same_seed_identical_score():
    scenario = compile_family_scenario("order_editing", default_context())
    persona = persona_by_id("loyal_regular")
    t1 = DialoguePolicy(scenario, persona, GoodMerchant(scenario), seed=5).run()
    t2 = DialoguePolicy(scenario, persona, GoodMerchant(scenario), seed=5).run()
    s1 = score_transcript(scenario, t1)
    s2 = score_transcript(scenario, t2)
    assert s1.headline == s2.headline
    assert s1.dimensions.as_dict() == s2.dimensions.as_dict()


def test_different_seed_may_differ_but_is_stable():
    scenario = compile_family_scenario("subscriptions", default_context())
    persona = persona_by_id("cautious_first_timer")
    # Each seed is internally stable even if seeds differ from each other.
    for seed in (1, 2, 3):
        a = DialoguePolicy(scenario, persona, GoodMerchant(scenario), seed=seed).run()
        b = DialoguePolicy(scenario, persona, GoodMerchant(scenario), seed=seed).run()
        assert _transcript_digest(a) == _transcript_digest(b)


def test_full_battery_run_is_reproducible():
    scenarios = compile_full_battery()
    personas = all_personas()
    run1 = run_battery(scenarios, personas,
                       adapter_factory=lambda s: GoodMerchant(s),
                       k_repeats=2, battery_version="t")
    run2 = run_battery(scenarios, personas,
                       adapter_factory=lambda s: GoodMerchant(s),
                       k_repeats=2, battery_version="t")
    d1 = {d.scenario_id: d.mean_headline() for d in run1.distributions}
    d2 = {d.scenario_id: d.mean_headline() for d in run2.distributions}
    assert d1 == d2
    assert run1.headline == run2.headline


def test_manifest_root_hash_stable_for_same_battery():
    scenarios = compile_full_battery()
    personas = all_personas()
    run1 = run_battery(scenarios, personas,
                       adapter_factory=lambda s: GoodMerchant(s),
                       k_repeats=1, battery_version="v")
    run2 = run_battery(scenarios, personas,
                       adapter_factory=lambda s: GoodMerchant(s),
                       k_repeats=1, battery_version="v")
    assert run1.manifest["root_hash"] == run2.manifest["root_hash"]
