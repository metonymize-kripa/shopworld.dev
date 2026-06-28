"""Shopper Simulator -- a deterministic, reproducible e-commerce shopper
behaviour simulator for grading single-shot web storefronts and multi-step
merchant agents against a frozen battery of shopper-intent tests.

Public API re-exports the things most callers need.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .adapters.dialogue_policy import DialoguePolicy, DialogueTranscript, PolicyConfig
from .adapters.mock_merchant import (
    CluelessMerchant,
    GoodMerchant,
    OvereagerMerchant,
    RefusingMerchant,
)
from .engine.rng import DeterministicRNG
from .engine.types import IntentLayer, Persona, Scenario, Vertical
from .oracle.scorer import ScenarioScore, score_transcript
from .orchestrator.runner import RunResult, run_battery
from .persona.library import all_personas, persona_by_id
from .reporting.scorecard import diff_runs, format_diff, format_scorecard
from .taxonomy.registry import HARD_CORE_MULTISTEP, all_families, family_by_id
from .taxonomy.scenario_compiler import (
    compile_family_scenario,
    compile_full_battery,
    compile_graph_journey,
    default_context,
)
from .taxonomy.graph import JourneyGraph, build_default_graph

__all__ = [
    "__version__",
    "DeterministicRNG",
    "IntentLayer",
    "Persona",
    "Scenario",
    "Vertical",
    "DialoguePolicy",
    "DialogueTranscript",
    "PolicyConfig",
    "GoodMerchant",
    "CluelessMerchant",
    "OvereagerMerchant",
    "RefusingMerchant",
    "ScenarioScore",
    "score_transcript",
    "RunResult",
    "run_battery",
    "all_personas",
    "persona_by_id",
    "all_families",
    "family_by_id",
    "HARD_CORE_MULTISTEP",
    "compile_family_scenario",
    "compile_full_battery",
    "compile_graph_journey",
    "default_context",
    "JourneyGraph",
    "build_default_graph",
    "diff_runs",
    "format_diff",
    "format_scorecard",
]
