"""Tests for scenario compilation and content-addressing."""

from __future__ import annotations

from shopper_sim.taxonomy.registry import HARD_CORE_MULTISTEP, all_families
from shopper_sim.taxonomy.scenario_compiler import (
    compile_family_scenario,
    compile_full_battery,
    default_context,
)


def test_compact_battery_one_scenario_per_family():
    battery = compile_full_battery(expand_overlays=False)
    assert len(battery) == len(all_families())


def test_overlay_expansion_adds_scenarios_for_multi_overlay_families():
    """Families with multiple overlays fan out to one scenario per overlay."""
    compact = compile_full_battery(expand_overlays=False)
    expanded = compile_full_battery(expand_overlays=True)
    # Every family contributes at least one scenario; multi-overlay families add
    # extras, so the expanded battery is strictly larger.
    assert len(expanded) > len(compact)
    # Each expanded scenario id is unique.
    assert len({s.scenario_id for s in expanded}) == len(expanded)


def test_multi_overlay_family_covers_all_its_overlays():
    """warranty_repair (electronics + home) yields a scenario for each."""
    expanded = compile_full_battery(expand_overlays=True)
    verticals = {s.vertical.value for s in expanded if "warranty_repair" in s.tags}
    assert "electronics" in verticals
    assert "home" in verticals


def test_scenario_ids_are_unique():
    battery = compile_full_battery()
    ids = [s.scenario_id for s in battery]
    assert len(ids) == len(set(ids))


def test_scenario_id_is_stable_content_hash():
    a = compile_family_scenario("order_editing", default_context())
    b = compile_family_scenario("order_editing", default_context())
    assert a.scenario_id == b.scenario_id


def test_hard_core_families_compile_to_multistep_scenarios():
    ctx = default_context()
    for fid in HARD_CORE_MULTISTEP:
        sc = compile_family_scenario(fid, ctx)
        assert sc.is_multistep, f"{fid} must compile to a multistep scenario"
        assert len(sc.goals) >= 2, f"{fid} must have a multi-goal stack"


def test_hard_core_scenarios_have_preconditioned_goal():
    """At least one goal in each hard-core scenario presupposes journey state."""
    ctx = default_context()
    for fid in HARD_CORE_MULTISTEP:
        sc = compile_family_scenario(fid, ctx)
        has_precondition = any(len(g.preconditions) > 0 for g in sc.goals)
        assert has_precondition, f"{fid} must have a preconditioned goal"


def test_goal_precondition_chain_is_satisfiable():
    """Every goal's preconditions are established by an earlier goal or the
    scenario's initial state -- i.e. the chain is internally consistent."""
    ctx = default_context()
    for fid in HARD_CORE_MULTISTEP:
        sc = compile_family_scenario(fid, ctx)
        established = set(sc.initial_state.keys())
        for goal in sc.goals:
            for pc in goal.preconditions:
                assert pc in established, (
                    f"{fid}: goal {goal.id} precondition {pc!r} never established"
                )
            established.update(goal.establishes)


def test_factsheet_only_contains_declared_knowledge():
    sc = compile_family_scenario("return_initiation", default_context())
    # The factsheet should carry at least the order id for a return.
    assert sc.factsheet.has("order_id")
