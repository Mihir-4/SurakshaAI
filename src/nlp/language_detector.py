"""Language detection with fastText when available, heuristic fallback otherwise."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)


class LanguageDetector:
    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or settings.fasttext_path
        self.model = None
        if self.model_path.exists():
            try:
                import fasttext

                self.model = fasttext.load_model(str(self.model_path))
            except Exception as exc:
                logger.warning("fastText language model unavailable: %s", exc)

    def detect(self, text: str) -> tuple[str, float]:
        value = str(text or "").strip()
        if not value:
            return "unknown", 0.0
        if self.model:
            labels, scores = self.model.predict(value.replace("\n", " "), k=1)
            return labels[0].replace("__label__", ""), float(scores[0])
        if re.search(r"[\u0900-\u097F]", value):
            return "hi", 0.55
        if re.search(r"[\u0A80-\u0AFF]", value):
            return "gu", 0.55
        if re.search(r"[\u0B80-\u0BFF]", value):
            return "ta", 0.55
        if re.search(r"[\u0C00-\u0C7F]", value):
            return "te", 0.55
        if re.search(r"[\u0C80-\u0CFF]", value):
            return "kn", 0.55
        if re.search(r"[\u0980-\u09FF]", value):
            return "bn", 0.55
        return "en", 0.50
