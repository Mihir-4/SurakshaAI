"""Sentence embedding helper."""

from __future__ import annotations

import numpy as np


class SentenceEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.model_name = model_name
        self.model = None

    def _load(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        self._load()
        return self.model.encode(texts, show_progress_bar=False)
