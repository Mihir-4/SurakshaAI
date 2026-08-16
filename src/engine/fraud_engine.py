"""End-to-end fraud analysis engine used by API and notebooks."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd
from scipy.sparse import hstack

from src.config import settings
from src.engine.rule_engine import RuleEngine
from src.engine.risk_scorer import RiskScorer
from src.models.url_model import URLFeatureExtractor
from src.models.upi_model import UPIFeatureExtractor
from src.preprocessing.feature_engineer import FeatureEngineer
from src.preprocessing.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class FraudDetectionEngine:
    def __init__(self, model_dir: Optional[Path] = None) -> None:
        self.model_dir = model_dir or settings.model_dir
        self.cleaner = TextCleaner()
        self.features = FeatureEngineer()
        self.rules = RuleEngine()
        self.scorer = RiskScorer()
        self.selected_models = self._load_selected_models()
        paths = self.selected_models.get("production_paths", {})

        self.ml_model = self._load_optional(Path(paths.get("text_ml") or settings.ml_model_dir / "best_text_ml.pkl"))
        self.vectorizer = self._load_optional(Path(paths.get("tfidf_vectorizer") or settings.ml_model_dir / "tfidf_vectorizer.pkl"))
        self.scaler = self._load_optional(Path(paths.get("feature_scaler") or settings.ml_model_dir / "feature_scaler.pkl"))
        self.url_bundle = self._load_optional(Path(paths.get("url") or settings.ml_model_dir / "url_model.pkl"))
        self.upi_bundle = self._load_optional(Path(paths.get("upi") or settings.ml_model_dir / "upi_model.pkl"))
        self.dl_model = None
        self.dl_tokenizer = None
        self.dl_device = "cpu"

# Production DL model is hosted on Hugging Face.
# Local path remains available as a fallback for development.
        if settings.HF_MODEL_ID:
            self._load_text_dl(settings.HF_MODEL_ID)
        elif paths.get("text_dl"):
            self._load_text_dl(Path(paths["text_dl"]))

    def _load_selected_models(self) -> dict:
        path = self.model_dir / "selected_models.json"
        if not path.exists():
            return {"production_paths": {}}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Could not read selected model config %s: %s", path, exc)
            return {"production_paths": {}}

    @staticmethod
    def _load_optional(path: Path) -> Any:
        try:
            return joblib.load(path) if path.exists() else None
        except Exception as exc:
            logger.warning("Could not load %s: %s", path, exc)
            return None

    def _load_text_dl(self, model_source: str | Path) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self.dl_device = "cuda" if torch.cuda.is_available() else "cpu"

            model_source = str(model_source)

            self.dl_tokenizer = AutoTokenizer.from_pretrained(model_source)
            self.dl_model = AutoModelForSequenceClassification.from_pretrained(
                model_source
            )

            self.dl_model.to(self.dl_device)
            self.dl_model.eval()

            logger.info(
                "Loaded selected DL model from %s on %s",
                model_source,
                self.dl_device,
            )

        except Exception as exc:
            logger.warning(
                "Could not load selected DL model from %s: %s",
                model_source,
                exc,
            )

    def predict_text_probability(self, text: str) -> tuple[float | None, dict]:
        cleaned = self.cleaner.clean(text)
        if not cleaned["is_valid"]:
            return None, cleaned
        if not all([self.ml_model, self.vectorizer, self.scaler]):
            return None, cleaned
        df = pd.DataFrame([{
            "cleaned_text": cleaned["cleaned_text"],
            "original_text": text,
        }])
        x_text = self.vectorizer.transform(df["cleaned_text"])
        x_num = self.scaler.transform(self.features.extract(df))
        score = float(self.ml_model.predict_proba(hstack([x_text, x_num]))[0, 1])
        return score, cleaned

    def predict_text_dl_probability(self, cleaned_text: str) -> float | None:
        if not self.dl_model or not self.dl_tokenizer:
            return None
        try:
            import torch

            encoded = self.dl_tokenizer(
                [cleaned_text],
                truncation=True,
                max_length=192,
                padding=True,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.dl_device) for key, value in encoded.items()}
            with torch.no_grad():
                logits = self.dl_model(**encoded).logits
                prob = torch.softmax(logits, dim=-1)[0, 1]
            return float(prob.detach().cpu().item())
        except Exception as exc:
            logger.warning("DL prediction failed: %s", exc)
            return None

    def analyze_text(self, text: str, channel: str = "sms", language: str = "auto") -> dict:
        ml_prob, cleaned = self.predict_text_probability(text)
        dl_prob = self.predict_text_dl_probability(cleaned.get("cleaned_text", ""))
        rule_hits = self.rules.evaluate_text(text)
        rule_score = self.rules.rule_score(rule_hits)
        risk_score = self.scorer.combine(
            ml_probability=ml_prob,
            dl_probability=dl_prob,
            rule_score=rule_score,
            rule_hits=rule_hits,
        )
        return {
            "channel": channel,
            "original_text": text,
            "cleaned_text": cleaned.get("cleaned_text", ""),
            "detected_language": language if language != "auto" else None,
            "risk_score": risk_score,
            "risk_level": self.scorer.level(risk_score),
            "ml_prediction": None if ml_prob is None else ("fraud" if ml_prob >= 0.5 else "safe"),
            "ml_confidence": ml_prob,
            "dl_prediction": None if dl_prob is None else ("fraud" if dl_prob >= 0.5 else "safe"),
            "dl_confidence": dl_prob,
            "rule_flags": [hit.flag for hit in rule_hits],
            "rule_evidence": [hit.evidence for hit in rule_hits],
            "shap_features": [],
            "model_versions": {
                "text_ml": (self.selected_models.get("text_ml") or {}).get("model_name"),
                "text_dl": (self.selected_models.get("text_dl") or {}).get("model_name"),
            },
        }

    def analyze_url(self, url: str) -> dict:
        extractor = URLFeatureExtractor()
        features = extractor.extract(pd.Series([url]))
        prob = None
        if self.url_bundle:
            prob = float(self.url_bundle["model"].predict_proba(features[self.url_bundle["features"]])[0, 1])
        score = self.scorer.combine(ml_probability=prob)
        return {
            "url": url,
            "url_features": features.iloc[0].to_dict(),
            "risk_score": score,
            "risk_level": self.scorer.level(score),
            "ml_prediction": None if prob is None else ("fraud" if prob >= 0.5 else "safe"),
            "ml_confidence": prob,
        }

    def analyze_upi(self, upi_string: str) -> dict:
        extractor = UPIFeatureExtractor()
        features = extractor.extract(pd.Series([upi_string]))
        prob = None
        if self.upi_bundle:
            prob = float(self.upi_bundle["model"].predict_proba(features[self.upi_bundle["features"]])[0, 1])
        score = self.scorer.combine(ml_probability=prob)
        return {
            "upi_string": upi_string,
            "upi_features": features.iloc[0].to_dict(),
            "risk_score": score,
            "risk_level": self.scorer.level(score),
            "ml_prediction": None if prob is None else ("fraud" if prob >= 0.5 else "safe"),
            "ml_confidence": prob,
        }
