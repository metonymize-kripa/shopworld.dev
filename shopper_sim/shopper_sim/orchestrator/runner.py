"""The run orchestrator.

Schedules a battery: scenarios x personas x seeds x K-repeats. The shopper side
is deterministic, so any variance across the K repeats is attributable to the
merchant under test -- that variance is itself a reported signal.

Produces a ``RunResult`` with per-scenario score distributions, layer roll-ups,
a headline, and a content-addressed manifest pinning all inputs.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..adapters.base import MerchantAdapter
from ..adapters.dialogue_policy import DialoguePolicy, PolicyConfig
from ..engine.hashing import Manifest, content_hash
from ..engine.types import Persona, Scenario
from ..oracle.rubric import RUBRIC_VERSION
from ..oracle.scorer import ScenarioScore, headline_score, rollup_by_layer, score_transcript

ENGINE_VERSION = "0.1.0"

# A factory builds a fresh adapter per run (so sessions are isolated).
AdapterFactory = Callable[[Scenario], MerchantAdapter]


@dataclass
class ScenarioDistribution:
    scenario_id: str
    persona_id: str
    title: str
    primary_layer: str
    scores: list[ScenarioScore] = field(default_factory=list)
    transcripts: list[dict] = field(default_factory=list)

    def mean_headline(self) -> float:
        return statistics.fmean(s.headline for s in self.scores) if self.scores else 0.0

    def stdev_headline(self) -> float:
        if len(self.scores) < 2:
            return 0.0
        return statistics.stdev(s.headline for s in self.scores)

    def as_dict(self) -> dict:
        d = {
            "scenario_id": self.scenario_id,
            "persona_id": self.persona_id,
            "title": self.title,
            "primary_layer": self.primary_layer,
            "mean_headline": self.mean_headline(),
            "stdev_headline": self.stdev_headline(),
            "k": len(self.scores),
            "samples": [s.as_dict() for s in self.scores],
        }
        if self.transcripts:
            d["transcripts"] = self.transcripts
        return d


@dataclass
class RunResult:
    battery_version: str
    headline: float
    layer_scores: dict[str, float]
    distributions: list[ScenarioDistribution]
    manifest: dict

    def as_dict(self) -> dict:
        return {
            "battery_version": self.battery_version,
            "headline": self.headline,
            "layer_scores": self.layer_scores,
            "distributions": [d.as_dict() for d in self.distributions],
            "manifest": self.manifest,
        }


def run_battery(
    scenarios: Sequence[Scenario],
    personas: Sequence[Persona],
    adapter_factory: AdapterFactory,
    base_seed: int = 1,
    k_repeats: int = 5,
    battery_version: str = "demo-1",
    policy_config: PolicyConfig | None = None,
    persona_mode: str = "recommended",
    capture_transcripts: bool = False,
) -> RunResult:
    """Run a battery and aggregate scores with K-repeat variance.

    ``persona_mode`` controls how personas are applied to each scenario:
      * ``"recommended"`` (default): one persona per scenario -- the scenario's
        recommended persona if set, else the first provided. Compact battery.
      * ``"cross"``: the full cross-product -- every scenario is run against
        every persona. This is the complete battery the manifest describes.

    With ``capture_transcripts=True`` the full per-run transcripts are retained
    on each distribution for audit/replay (larger result; off by default).
    """
    if persona_mode not in ("recommended", "cross"):
        raise ValueError(f"unknown persona_mode {persona_mode!r}")
    if not personas:
        raise ValueError("no personas provided")

    distributions: list[ScenarioDistribution] = []
    all_scores: list[ScenarioScore] = []

    for scenario in scenarios:
        if persona_mode == "cross":
            run_personas = list(personas)
        else:
            run_personas = [_select_persona(scenario, personas)]

        for persona in run_personas:
            dist = ScenarioDistribution(
                scenario_id=scenario.scenario_id,
                persona_id=persona.id,
                title=scenario.title,
                primary_layer=scenario.primary_layer.value,
            )
            for k in range(k_repeats):
                seed = _run_seed(base_seed, scenario.scenario_id, persona.id, k)
                adapter = adapter_factory(scenario)
                policy = DialoguePolicy(scenario, persona, adapter, seed, policy_config)
                transcript = policy.run()
                score = score_transcript(scenario, transcript)
                dist.scores.append(score)
                all_scores.append(score)
                if capture_transcripts:
                    dist.transcripts.append(transcript.to_dict())
            distributions.append(dist)

    layer_scores = rollup_by_layer(all_scores)
    headline = headline_score(all_scores)

    # The manifest reflects what was actually run, including persona_mode.
    used_personas = (
        [p.id for p in personas]
        if persona_mode == "cross"
        else sorted({d.persona_id for d in distributions})
    )
    artifact_hashes = {
        "scenarios": content_hash([s.scenario_id for s in scenarios]),
        "personas": content_hash(sorted(used_personas)),
        "persona_mode": persona_mode,
        "rubric_version": RUBRIC_VERSION,
        "k_repeats": str(k_repeats),
        "base_seed": str(base_seed),
    }
    manifest = Manifest(
        engine_version=ENGINE_VERSION,
        battery_version=battery_version,
        artifact_hashes=artifact_hashes,
    ).to_dict()

    return RunResult(
        battery_version=battery_version,
        headline=headline,
        layer_scores=layer_scores,
        distributions=distributions,
        manifest=manifest,
    )


def _select_persona(scenario: Scenario, personas: Sequence[Persona]) -> Persona:
    if scenario.recommended_persona_id:
        for p in personas:
            if p.id == scenario.recommended_persona_id:
                return p
    if not personas:
        raise ValueError("no personas provided")
    return personas[0]


def _run_seed(base_seed: int, scenario_id: str, persona_id: str, k: int) -> int:
    from ..engine.rng import derive_seed

    return derive_seed(base_seed, f"{scenario_id}:{persona_id}:{k}")
