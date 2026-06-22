"""Shallow linear intent classifier (SVM/FastText-style).

A bag-of-words linear model trained with deterministic gradient descent. This is
the "shallow classification baseline" milli.run owns (README §7). We use a
numpy-only linear model rather than a FastText/libsvm binary so the agent runs
anywhere and stays fully deterministic; the architecture (linear model over
bag-of-words features + confidence) matches the spec's intent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from milli_run.nlu.training_data import TRAINING_UTTERANCES

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


@dataclass
class Intent:
    label: str
    confidence: float
    scores: Dict[str, float]


class LinearIntentClassifier:
    """One-vs-rest logistic regression over binary bag-of-words features."""

    def __init__(
        self,
        training: Optional[List[Tuple[str, str]]] = None,
        epochs: int = 300,
        lr: float = 0.5,
        l2: float = 1e-3,
        seed: int = 0,
    ):
        self.epochs = epochs
        self.lr = lr
        self.l2 = l2
        self.seed = seed
        self.vocab: Dict[str, int] = {}
        self.labels: List[str] = []
        self.W: Optional[np.ndarray] = None  # (n_labels, n_features)
        self.b: Optional[np.ndarray] = None  # (n_labels,)
        self._train(training or TRAINING_UTTERANCES)

    def _vectorize(self, text: str) -> np.ndarray:
        vec = np.zeros(len(self.vocab), dtype=np.float64)
        for tok in _tokenize(text):
            idx = self.vocab.get(tok)
            if idx is not None:
                vec[idx] = 1.0
        return vec

    def _train(self, data: List[Tuple[str, str]]) -> None:
        # Build vocabulary and label set deterministically.
        vocab: Dict[str, int] = {}
        for text, _label in data:
            for tok in _tokenize(text):
                if tok not in vocab:
                    vocab[tok] = len(vocab)
        self.vocab = vocab
        self.labels = sorted({label for _t, label in data})
        label_idx = {label: i for i, label in enumerate(self.labels)}

        X = np.stack([self._vectorize(t) for t, _ in data]) if data else np.zeros((0, 0))
        Y = np.zeros((len(data), len(self.labels)), dtype=np.float64)
        for row, (_t, label) in enumerate(data):
            Y[row, label_idx[label]] = 1.0

        n_features = len(self.vocab)
        n_labels = len(self.labels)
        rng = np.random.RandomState(self.seed)
        self.W = rng.normal(0, 0.01, size=(n_labels, n_features))
        self.b = np.zeros(n_labels)

        n = max(len(data), 1)
        for _ in range(self.epochs):
            logits = X @ self.W.T + self.b  # (n, n_labels)
            probs = 1.0 / (1.0 + np.exp(-logits))
            err = probs - Y  # (n, n_labels)
            grad_W = err.T @ X / n + self.l2 * self.W
            grad_b = err.mean(axis=0)
            self.W -= self.lr * grad_W
            self.b -= self.lr * grad_b

    def predict(self, text: str) -> Intent:
        if self.W is None or not self.labels:
            return Intent("OTHER", 0.0, {})
        x = self._vectorize(text)
        logits = self.W @ x + self.b
        # Softmax for a calibrated-ish confidence across labels.
        z = logits - logits.max()
        exp = np.exp(z)
        probs = exp / exp.sum()
        scores = {label: float(probs[i]) for i, label in enumerate(self.labels)}
        best = int(np.argmax(probs))
        return Intent(self.labels[best], float(probs[best]), scores)
