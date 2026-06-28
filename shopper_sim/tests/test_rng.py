"""Tests for the deterministic RNG primitives."""

from __future__ import annotations

import pytest

from shopper_sim.engine.rng import DeterministicRNG, derive_seed


def test_same_seed_same_sequence():
    a = DeterministicRNG(123)
    b = DeterministicRNG(123)
    seq_a = [a.random() for _ in range(50)]
    seq_b = [b.random() for _ in range(50)]
    assert seq_a == seq_b


def test_different_seed_different_sequence():
    a = DeterministicRNG(1)
    b = DeterministicRNG(2)
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_derive_is_deterministic():
    s1 = derive_seed(42, "behavior")
    s2 = derive_seed(42, "behavior")
    assert s1 == s2
    assert derive_seed(42, "behavior") != derive_seed(42, "nlg")


def test_derived_streams_are_independent_and_stable():
    parent = DeterministicRNG(7)
    child_a1 = parent.derive("a")
    child_a2 = DeterministicRNG(7).derive("a")
    assert [child_a1.random() for _ in range(5)] == [child_a2.random() for _ in range(5)]


def test_weighted_choice_distribution():
    rng = DeterministicRNG(99)
    counts = {"x": 0, "y": 0}
    for _ in range(2000):
        counts[rng.weighted_choice(["x", "y"], [3.0, 1.0])] += 1
    # x should be roughly 3x y; allow generous tolerance
    assert counts["x"] > counts["y"] * 2


def test_weighted_choice_rejects_bad_weights():
    rng = DeterministicRNG(1)
    with pytest.raises(ValueError):
        rng.weighted_choice(["a", "b"], [0.0, 0.0])
    with pytest.raises(ValueError):
        rng.weighted_choice(["a"], [1.0, 2.0])


def test_shuffled_does_not_mutate_input():
    rng = DeterministicRNG(5)
    original = [1, 2, 3, 4, 5]
    shuffled = rng.shuffled(original)
    assert original == [1, 2, 3, 4, 5]
    assert sorted(shuffled) == original


def test_sample_distinct():
    rng = DeterministicRNG(5)
    picked = rng.sample(list(range(10)), 4)
    assert len(picked) == 4
    assert len(set(picked)) == 4


def test_bernoulli_bounds():
    rng = DeterministicRNG(3)
    assert all(rng.bernoulli(1.0) for _ in range(10))
    assert not any(rng.bernoulli(0.0) for _ in range(10))


def test_negative_seed_rejected():
    with pytest.raises(ValueError):
        DeterministicRNG(-1)
