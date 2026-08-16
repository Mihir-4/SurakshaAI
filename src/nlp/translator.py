"""Translation abstraction for IndicTrans2 or no-op fallback."""

from __future__ import annotations


class IndicTranslator:
    """Placeholder-compatible translator.

    On Kaggle, you can replace this implementation with IndicTrans2 model loading.
    The production engine can still run because the fallback preserves the text.
    """

    def translate(self, text: str, src: str = "auto", tgt: str = "en") -> str:
        return str(text or "")
