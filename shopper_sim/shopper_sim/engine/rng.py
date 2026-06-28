"""Deterministic random-number primitives.

The entire simulator draws randomness from a SINGLE seeded stream that is
threaded explicitly through every stochastic call. This module is the only
sanctioned source of randomness in the engine.

Hard rules (enforced by tests and the import-linter contract):
  * Never import the stdlib ``random`` module in engine code.
  * Never call bare ``numpy.random.*`` (the global, unseeded RNG).
  * Never read the wall clock inside the engine.

A :class:`DeterministicRNG` wraps ``numpy.random.Generator(PCG64(seed))`` and
exposes a small, audited surface. Sub-streams are derived deterministically by
hashing a label into a child seed, so independent subsystems (behavior, NLG,
dialogue policy) can each hold their own reproducible stream without stepping
on one another.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence, TypeVar

import numpy as np
from numpy.random import PCG64, Generator

T = TypeVar("T")

_LABEL_ENCODING = "utf-8"


def derive_seed(parent_seed: int, label: str) -> int:
    """Derive a child seed deterministically from a parent seed and a label.

    Uses BLAKE2b so the mapping is stable across processes and Python versions
    (unlike ``hash()``, which is salted by ``PYTHONHASHSEED``). Returns a 63-bit
    non-negative integer suitable as a NumPy seed.
    """
    h = hashlib.blake2b(digest_size=8)
    h.update(parent_seed.to_bytes(8, "big", signed=False))
    h.update(b"\x00")
    h.update(label.encode(_LABEL_ENCODING))
    return int.from_bytes(h.digest(), "big") & ((1 << 63) - 1)


@dataclass(frozen=True)
class RNGState:
    """A serialisable snapshot of an RNG's position, for audit/replay."""

    seed: int
    bit_generator_state: dict


class DeterministicRNG:
    """A thin, audited wrapper over a single PCG64 stream.

    All methods are pure functions of the construction seed and the sequence of
    prior calls. Two ``DeterministicRNG`` objects built from the same seed and
    driven through the same call sequence yield byte-identical results.
    """

    __slots__ = ("_seed", "_gen")

    def __init__(self, seed: int) -> None:
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self._seed = int(seed)
        self._gen: Generator = Generator(PCG64(self._seed))

    @property
    def seed(self) -> int:
        return self._seed

    def derive(self, label: str) -> "DeterministicRNG":
        """Return an independent child stream keyed by ``label``."""
        return DeterministicRNG(derive_seed(self._seed, label))

    # -- core draws ---------------------------------------------------------

    def random(self) -> float:
        """A float in [0, 1)."""
        return float(self._gen.random())

    def randint(self, low: int, high: int) -> int:
        """An int in [low, high) (high exclusive)."""
        if high <= low:
            raise ValueError(f"empty range [{low}, {high})")
        return int(self._gen.integers(low, high))

    def choice(self, items: Sequence[T]) -> T:
        """Uniformly pick one item. ``items`` must be an ordered sequence."""
        if len(items) == 0:
            raise ValueError("cannot choose from an empty sequence")
        idx = int(self._gen.integers(0, len(items)))
        return items[idx]

    def weighted_choice(self, items: Sequence[T], weights: Sequence[float]) -> T:
        """Pick one item with probability proportional to its weight.

        Weights need not be normalised but must be non-negative and sum > 0.
        Determinism note: we sample via inverse-CDF over the *ordered* inputs
        rather than ``Generator.choice`` with ``p=`` so behaviour is stable and
        easy to reason about.
        """
        if len(items) != len(weights):
            raise ValueError("items and weights length mismatch")
        if len(items) == 0:
            raise ValueError("cannot choose from an empty sequence")
        total = 0.0
        for w in weights:
            if w < 0:
                raise ValueError("weights must be non-negative")
            total += w
        if total <= 0.0:
            raise ValueError("weights must sum to a positive value")
        target = self._gen.random() * total
        cumulative = 0.0
        for item, w in zip(items, weights):
            cumulative += w
            if target < cumulative:
                return item
        return items[-1]  # floating-point fallthrough

    def bernoulli(self, p: float) -> bool:
        """True with probability ``p``."""
        if not 0.0 <= p <= 1.0:
            raise ValueError("p must be in [0, 1]")
        return bool(self._gen.random() < p)

    def shuffled(self, items: Sequence[T]) -> list[T]:
        """Return a new shuffled list (does not mutate the input)."""
        out = list(items)
        # Fisher-Yates using the seeded generator for explicit determinism.
        for i in range(len(out) - 1, 0, -1):
            j = int(self._gen.integers(0, i + 1))
            out[i], out[j] = out[j], out[i]
        return out

    def sample(self, items: Sequence[T], k: int) -> list[T]:
        """Pick ``k`` distinct items, order deterministic given the seed."""
        if k < 0:
            raise ValueError("k must be non-negative")
        if k > len(items):
            raise ValueError("k larger than population")
        return self.shuffled(items)[:k]

    # -- audit --------------------------------------------------------------

    def snapshot(self) -> RNGState:
        return RNGState(seed=self._seed, bit_generator_state=self._gen.bit_generator.state)
