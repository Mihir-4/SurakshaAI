"""Calibration helpers for probability outputs."""

from __future__ import annotations

import numpy as np


class TemperatureScaler:
    """Simple temperature scaling for binary logits."""

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = max(float(temperature), 1e-6)

    def predict_proba(self, logits) -> np.ndarray:
        logits = np.asarray(logits, dtype=float) / self.temperature
        if logits.ndim == 1:
            probs = 1.0 / (1.0 + np.exp(-logits))
            return np.column_stack([1.0 - probs, probs])
        shifted = logits - logits.max(axis=1, keepdims=True)
        exp = np.exp(shifted)
        return exp / exp.sum(axis=1, keepdims=True)
