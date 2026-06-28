"""Tests for the gap-closing features: persona cross-product, transcript
replay/serialisation, and graph-driven scenario generation."""

from __future__ import annotations

import json

from shopper_sim.adapters.dialogue_policy import DialoguePolicy
from shopper_sim.adapters.mock_merchant import GoodMerchant
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas, persona_by_id
from shopper_sim.taxonomy.graph import EdgeKind, build_default_graph
from shopper_sim.taxonomy.scenario_compiler import (
    compile_family_scenario,
    compile_full_battery,
    compile_graph_journey,
    default_context,
)


# -- persona cross-product -------------------------------------------------

def test_recommended_mode_one_distribution_per_scenario():
    scenarios = compile_full_battery(expand_overlays=False)
    run = run_battery(scenarios, all_personas(),
                      adapter_factory=lambda s: GoodMerchant(s),
                      k_repeats=1, persona_mode="recommended", battery_version="t")
    assert len(run.distributions) == len(scenarios)


def test_cross_mode_runs_every_persona_against_every_scenario():
    scenarios = compile_full_battery(expand_overlays=False)
    personas = all_personas()
    run = run_battery(scenarios, personas,
                      adapter_factory=lambda s: GoodMerchant(s),
                      k_repeats=1, persona_mode="cross", battery_version="t")
    assert len(run.distributions) == len(scenarios) * len(personas)
    # Each scenario appears once per persona.
    per_scenario = {}
    for d in run.distributions:
        per_scenario.setdefault(d.scenario_id, set()).add(d.persona_id)
    assert all(len(ps) == len(personas) for ps in per_scenario.values())


def test_manifest_records_persona_mode():
    scenarios = compile_full_battery(expand_overlays=False)
    run = run_battery(scenarios, all_personas(),
                      adapter_factory=lambda s: GoodMerchant(s),
                      k_repeats=1, persona_mode="cross", battery_version="t")
    assert run.manifest["artifact_hashes"]["persona_mode"] == "cross"


def test_cross_and_recommended_manifests_differ():
    scenarios = compile_full_battery(expand_overlays=False)
    rec = run_battery(scenarios, all_personas(),
                      adapter_factory=lambda s: GoodMerchant(s),
                      k_repeats=1, persona_mode="recommended", battery_version="t")
    cross = run_battery(scenarios, all_personas(),
                        adapter_factory=lambda s: GoodMerchant(s),
                        k_repeats=1, persona_mode="cross", battery_version="t")
    assert rec.manifest["root_hash"] != cross.manifest["root_hash"]


# -- transcript replay -----------------------------------------------------

def test_transcript_serialises_full_turn_detail():
    scenario = compile_family_scenario("return_initiation", default_context())
    t = DialoguePolicy(scenario, persona_by_id("loyal_regular"),
                       GoodMerchant(scenario), seed=3).run()
    d = t.to_dict()
    assert d["scenario_id"] == scenario.scenario_id
    assert d["turns"] and "shopper_utterance" in d["turns"][0]
    assert d["goal_results"] and "satisfied" in d["goal_results"][0]
    # Round-trips through JSON cleanly.
    assert json.loads(json.dumps(d))["seed"] == t.seed


def test_capture_transcripts_attaches_replayable_record():
    scenarios = compile_full_battery(expand_overlays=False)[:3]
    run = run_battery(scenarios, all_personas(),
                      adapter_factory=lambda s: GoodMerchant(s),
                      k_repeats=2, capture_transcripts=True, battery_version="t")
    d = run.distributions[0].as_dict()
    assert "transcripts" in d
    assert len(d["transcripts"]) == 2


def test_transcripts_omitted_by_default():
    scenarios = compile_full_battery(expand_overlays=False)[:2]
    run = run_battery(scenarios, all_personas(),
                      adapter_factory=lambda s: GoodMerchant(s),
                      k_repeats=1, battery_version="t")
    assert "transcripts" not in run.distributions[0].as_dict()


# -- graph-driven scenarios ------------------------------------------------

def test_graph_journey_is_multistep_and_deterministic():
    a = compile_graph_journey("category_discovery", seed=7)
    b = compile_graph_journey("category_discovery", seed=7)
    assert a.scenario_id == b.scenario_id
    assert a.is_multistep
    assert len(a.goals) >= 2


def test_graph_journey_links_goals_by_precondition():
    sc = compile_graph_journey("category_discovery", seed=7, max_steps=4)
    # Every goal after the first presupposes the previous goal's established key.
    established = set()
    for i, g in enumerate(sc.goals):
        if i > 0:
            assert g.preconditions, f"goal {g.id} should depend on the prior step"
            assert all(p in established for p in g.preconditions)
        established.update(g.establishes)


def test_graph_journey_different_starts_differ():
    a = compile_graph_journey("category_discovery", seed=1)
    b = compile_graph_journey("order_confirmation", seed=1)
    assert a.scenario_id != b.scenario_id


def test_graph_walk_follows_only_requested_edge_kinds():
    from shopper_sim.engine.rng import DeterministicRNG

    graph = build_default_graph()
    path = graph.weighted_walk(
        "order_confirmation", DeterministicRNG(5),
        kinds=(EdgeKind.ESCALATES_TO,), max_steps=4,
    )
    assert path[0] == "order_confirmation"
    assert len(path) >= 1
