"""URL feature extraction and XGBoost/sklearn training."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from urllib.parse import urlparse

import joblib
import pandas as pd
import tldextract
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from src.config import settings
from src.preprocessing.label_mapper import LabelMapper
from src.models.ml_trainer import binary_metrics

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly"}
SUSPICIOUS_WORDS = ["login", "verify", "secure", "update", "bank", "kyc", "otp", "free", "claim"]


def entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    total = len(value)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


class URLFeatureExtractor:
    def extract_one(self, url: str) -> dict:
        raw = str(url or "").strip()
        normalized = raw if re.match(r"^[a-z]+://", raw, re.I) else "http://" + raw
        parse_error = 0
        try:
            parsed = urlparse(normalized)
        except ValueError:
            parse_error = 1
            parsed = urlparse("http://invalid.local/")
        try:
            ext = tldextract.extract(raw)
        except Exception:
            ext = tldextract.extract("invalid.local")
        domain = ".".join(part for part in [ext.domain, ext.suffix] if part)
        host = parsed.netloc.lower()
        return {
            "url_length": len(raw),
            "domain_length": len(domain),
            "path_length": len(parsed.path or ""),
            "num_dots": raw.count("."),
            "num_hyphens": raw.count("-"),
            "num_digits": sum(c.isdigit() for c in raw),
            "num_params": len(parsed.query.split("&")) if parsed.query else 0,
            "has_https": int(parsed.scheme == "https"),
            "has_ip_address": int(bool(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", host))),
            "has_at_symbol": int("@" in raw),
            "parse_error": parse_error,
            "has_shortener": int(domain in SHORTENERS),
            "suspicious_kw_count": sum(word in raw.lower() for word in SUSPICIOUS_WORDS),
            "domain_entropy": round(entropy(domain), 4),
            "url_entropy": round(entropy(raw), 4),
        }

    def extract(self, urls: pd.Series) -> pd.DataFrame:
        return pd.DataFrame([self.extract_one(u) for u in urls])


class URLModelTrainer:
    def __init__(self) -> None:
        self.extractor = URLFeatureExtractor()

    def train(self, df: pd.DataFrame, url_col: str = "url", label_col: str = "label") -> dict:
        mapper = LabelMapper()
        df = mapper.apply(df, label_col=label_col)
        df = mapper.drop_unknown(df)
        df = mapper.add_binary_label(df)
        x = self.extractor.extract(df[url_col])
        y = df["label_binary"].astype(int)
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, stratify=y, random_state=settings.RANDOM_SEED
        )
        try:
            from xgboost import XGBClassifier

            model = XGBClassifier(
                n_estimators=350,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=settings.RANDOM_SEED,
            )
        except Exception:
            model = RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced",
                random_state=settings.RANDOM_SEED,
                n_jobs=-1,
            )
        model.fit(x_train, y_train)
        score = model.predict_proba(x_test)[:, 1]
        pred = (score >= 0.5).astype(int)
        metrics = binary_metrics(y_test, pred, score)
        settings.ml_model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "features": list(x.columns)}, settings.ml_model_dir / "url_model.pkl")
        return metrics

    @staticmethod
    def checksum(url: str) -> str:
        return hashlib.sha256(str(url).encode("utf-8")).hexdigest()
