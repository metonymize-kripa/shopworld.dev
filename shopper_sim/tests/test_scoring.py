"""Tests for the oracle/scorer and reporting/diff."""

from __future__ import annotations

from shopper_sim.adapters.mock_merchant import (
    CluelessMerchant,
    GoodMerchant,
    OvereagerMerchant,
)
from shopper_sim.oracle.rubric import DIMENSION_WEIGHTS, DimensionScores
from shopper_sim.orchestrator.runner import run_battery
from shopper_sim.persona.library import all_personas
from shopper_sim.reporting.scorecard import diff_runs, format_diff, format_scorecard
from shopper_sim.taxonomy.scenario_compiler import compile_full_battery


def _run(merchant_cls, k=3, version="t"):
    scenarios = compile_full_battery()
    return run_battery(scenarios, all_personas(),
                       adapter_factory=lambda s: merchant_cls(s),
                       k_repeats=k, battery_version=version)


def test_dimension_weights_sum_positive():
    assert sum(DIMENSION_WEIGHTS.values()) > 0


def test_weighted_total_bounds():
    perfect = DimensionScores(1, 1, 1, 1, 1)
    zero = DimensionScores(0, 0, 0, 0, 0)
    assert perfect.weighted_total() == 1.0
    assert zero.weighted_total() == 0.0


def test_good_beats_clueless():
    good = _run(GoodMerchant)
    clueless = _run(CluelessMerchant)
    assert good.headline > clueless.headline + 0.3  # large, clear gap


def test_good_beats_or_matches_overeager_overall():
    good = _run(GoodMerchant)
    overeager = _run(OvereagerMerchant)
    # Good should never score below Overeager overall.
    assert good.headline >= overeager.headline


def test_overeager_loses_on_exception_layer():
    """Skipping info-gathering should cost the exception layer specifically."""
    good = _run(GoodMerchant)
    overeager = _run(OvereagerMerchant)
    assert good.layer_scores["exception"] >= overeager.layer_scores["exception"]


def test_headline_in_unit_range():
    run = _run(GoodMerchant)
    assert 0.0 <= run.headline <= 1.0
    for layer, score in run.layer_scores.items():
        assert 0.0 <= score <= 1.0


def test_diff_same_battery_flag_true():
    before = _run(CluelessMerchant, version="same")
    after = _run(GoodMerchant, version="same")
    diff = diff_runs(before, after)
    assert diff.same_battery
    assert diff.headline_delta > 0
    assert len(diff.improvements) > 0


def test_diff_detects_regression():
    before = _run(GoodMerchant, version="same")
    after = _run(CluelessMerchant, version="same")
    diff = diff_runs(before, after)
    assert diff.headline_delta < 0
    assert len(diff.regressions) > 0


def test_scorecard_and_diff_render_without_error():
    run = _run(GoodMerchant)
    card = format_scorecard(run)
    assert "Headline score" in card
    before = _run(CluelessMerchant, version="same")
    after = _run(GoodMerchant, version="same")
    text = format_diff(diff_runs(before, after))
    assert "Headline" in text


def test_krepeats_variance_is_bounded_for_deterministic_merchant():
    """K-repeats intentionally vary the shopper's *phrasing* (each repeat uses a
    different seed) to probe merchant robustness. With a deterministic merchant
    the score variance should therefore be small but need not be exactly zero.
    Per-seed determinism is guaranteed separately (see test_determinism)."""
    run = _run(GoodMerchant, k=4)
    for d in run.distributions:
        assert d.stdev_headline() <= 0.35


def test_per_repeat_scores_are_individually_reproducible():
    """Re-running the exact same battery reproduces every per-scenario score."""
    run_a = _run(GoodMerchant, k=3, version="repro")
    run_b = _run(GoodMerchant, k=3, version="repro")
    a = {d.scenario_id: [s.headline for s in d.scores] for d in run_a.distributions}
    b = {d.scenario_id: [s.headline for s in d.scores] for d in run_b.distributions}
    assert a == b
