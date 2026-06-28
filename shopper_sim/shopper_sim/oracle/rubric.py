"""The scoring rubric.

Each scenario run yields sub-scores across rubric dimensions; these roll up to
per-intent-layer scores and a single headline number. Weights are PUBLIC and
versioned so merchants trust the ruler.

Dimensions:
  * task_success  -- did the goal stack complete?
  * efficiency    -- turns/clicks relative to optimal.
  * correctness   -- right info asked for; impossible asks penalised.
  * disclosure    -- trust/fee/policy disclosure (where applicable).
  * recovery      -- graceful handling of exceptions / ambiguity.
"""

from __future__ import annotations

from dataclasses import dataclass

# Frozen, versioned rubric weights (sum need not be 1; normalised at roll-up).
RUBRIC_VERSION = "1.0.0"

DIMENSION_WEIGHTS: dict[str, float] = {
    "task_success": 0.40,
    "efficiency": 0.15,
    "correctness": 0.25,
    "disclosure": 0.10,
    "recovery": 0.10,
}


@dataclass(frozen=True)
class DimensionScores:
    task_success: float
    efficiency: float
    correctness: float
    disclosure: float
    recovery: float

    def as_dict(self) -> dict[str, float]:
        return {
            "task_success": self.task_success,
            "efficiency": self.efficiency,
            "correctness": self.correctness,
            "disclosure": self.disclosure,
            "recovery": self.recovery,
        }

    def weighted_total(self) -> float:
        total_w = sum(DIMENSION_WEIGHTS.values())
        s = sum(getattr(self, dim) * w for dim, w in DIMENSION_WEIGHTS.items())
        return s / total_w
