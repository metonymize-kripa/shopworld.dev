"""Coverage tests: the battery must exercise the full taxonomy."""

from __future__ import annotations

from shopper_sim.engine.types import IntentLayer
from shopper_sim.taxonomy.registry import (
    HARD_CORE_MULTISTEP,
    all_families,
    families_by_layer,
    family_by_id,
    family_by_number,
)


def test_exactly_52_families():
    fams = all_families()
    assert len(fams) == 52


def test_family_numbers_are_1_to_52_unique():
    numbers = sorted(f.number for f in all_families())
    assert numbers == list(range(1, 53))


def test_family_ids_unique():
    ids = [f.id for f in all_families()]
    assert len(ids) == len(set(ids))


def test_lookup_by_id_and_number_consistent():
    for f in all_families():
        assert family_by_id(f.id) is f
        assert family_by_number(f.number) is f


def test_all_primary_layers_present():
    """Every intent layer except VERTICAL is a primary classification.

    VERTICAL is an overlay modifier (per the taxonomy design), not a family's
    primary layer, so it is intentionally absent from primary_layer values.
    """
    present = {f.layer for f in all_families()}
    expected = set(IntentLayer) - {IntentLayer.VERTICAL}
    assert present == expected


def test_each_primary_layer_has_at_least_one_family():
    for layer in IntentLayer:
        if layer == IntentLayer.VERTICAL:
            continue
        assert len(families_by_layer(layer)) >= 1


def test_hard_core_multistep_are_all_known_and_multistep():
    for fid in HARD_CORE_MULTISTEP:
        fam = family_by_id(fid)
        assert fam.is_multistep, f"{fid} should be multistep"


def test_hard_core_multistep_count():
    assert len(HARD_CORE_MULTISTEP) == 12


def test_multistep_families_outnumber_single_shot():
    fams = all_families()
    multi = [f for f in fams if f.is_multistep]
    # The taxonomy is dominated by multi/escalating families.
    assert len(multi) > len(fams) / 2
