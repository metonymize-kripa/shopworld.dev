"""Bitext importers, leakage controls, NLU augmentation, 30-scenario set."""

from shopworld.scenarios import (
    import_support_utterances,
    import_retail_utterances,
    assert_no_leakage,
    split_report,
)
from shopworld.scenarios.splits import Split
from shopworld.tasks import mvp_task_set

from milli_run.nlu.svm_model import LinearIntentClassifier
from milli_run.nlu.corpus import augmented_training, bitext_training


def test_support_importer_volume_and_provenance():
    utts = import_support_utterances()
    assert len(utts) >= 500  # README §10: 500 support-derived utterances
    assert all(u.domain == "support" for u in utts)
    assert all(u.source in ("bitext", "synthetic") for u in utts)


def test_retail_importer_volume():
    utts = import_retail_utterances()
    assert len(utts) >= 500


def test_no_leakage_across_splits():
    utts = import_support_utterances() + import_retail_utterances()
    assert assert_no_leakage(utts) is True


def test_split_distribution_reasonable():
    report = split_report(import_support_utterances())
    # All three splits populated; train is the largest.
    assert report[Split.NLU_TRAIN.value] > report[Split.HELDOUT_TEST.value] > 0


def test_bitext_training_excludes_heldout():
    train_texts = {t for t, _ in bitext_training(Split.NLU_TRAIN)}
    heldout = {u.text for u in import_support_utterances() if u.split == Split.HELDOUT_TEST}
    assert not (train_texts & heldout)  # leakage rule


def test_augmented_classifier_generalizes_to_heldout():
    """Train on built-in + Bitext nlu_train, evaluate on held-out test split."""
    clf = LinearIntentClassifier(training=augmented_training(), epochs=200)
    heldout = [
        u for u in import_support_utterances()
        if u.split == Split.HELDOUT_TEST and u.intent in
        {"WISMO", "CANCEL", "REFUND", "RETURN", "ADDRESS_CHANGE"}
    ]
    assert heldout, "expected some held-out actionable utterances"
    correct = sum(1 for u in heldout if clf.predict(u.text).label == u.intent)
    accuracy = correct / len(heldout)
    assert accuracy >= 0.8  # shallow model should generalize on clean splits


def test_mvp_task_set_has_30_scenarios():
    tasks = mvp_task_set()
    assert len(tasks) == 30
    assert len({t.id for t in tasks}) == 30  # all distinct
