"""Synthetic UPI data generation, feature extraction, and model training."""

from __future__ import annotations

import random
from urllib.parse import parse_qs, urlparse

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from src.config import settings
from src.models.ml_trainer import binary_metrics


TRUSTED_HANDLES = ["oksbi", "okhdfcbank", "okaxis", "okicici", "ybl", "upi", "paytm"]
RISKY_HANDLES = ["refund", "cashback", "rbi", "support", "verify", "loan"]


class UPIFeatureExtractor:
    def parse(self, upi_string: str) -> dict:
        value = str(upi_string or "")
        parsed = urlparse(value)
        qs = parse_qs(parsed.query)
        pa = qs.get("pa", [""])[0]
        pn = qs.get("pn", [""])[0]
        tn = qs.get("tn", [""])[0]
        amount = qs.get("am", [""])[0]
        handle = pa.split("@")[-1].lower() if "@" in pa else ""
        try:
            amount_value = float(amount) if amount else 0.0
        except ValueError:
            amount_value = 0.0
        return {"vpa": pa, "payee_name": pn, "transaction_note": tn, "amount": amount_value, "handle": handle}

    def extract_one(self, upi_string: str) -> dict:
        parsed = self.parse(upi_string)
        joined = " ".join([parsed["vpa"], parsed["payee_name"], parsed["transaction_note"]]).lower()
        return {
            "vpa_length": len(parsed["vpa"]),
            "payee_length": len(parsed["payee_name"]),
            "note_length": len(parsed["transaction_note"]),
            "amount": parsed["amount"],
            "has_amount": int(parsed["amount"] > 0),
            "high_amount": int(parsed["amount"] >= 5000),
            "trusted_handle": int(parsed["handle"] in TRUSTED_HANDLES),
            "risky_handle_word": int(any(w in parsed["handle"] for w in RISKY_HANDLES)),
            "refund_keyword": int("refund" in joined or "reversal" in joined),
            "urgency_keyword": int(any(w in joined for w in ["urgent", "verify", "kyc", "blocked", "claim"])),
            "numeric_vpa": int(parsed["vpa"].split("@")[0].isdigit()) if parsed["vpa"] else 0,
        }

    def extract(self, series: pd.Series) -> pd.DataFrame:
        return pd.DataFrame([self.extract_one(v) for v in series])


def generate_synthetic_upi(n: int = 5000) -> pd.DataFrame:
    random.seed(settings.RANDOM_SEED)
    rows = []
    merchants = ["amazon", "swiggy", "electricityboard", "licindia", "irctc", "dmart"]
    scam_names = ["rbi refund", "kyc support", "cashback claim", "loan approval", "upi helpdesk"]
    for i in range(n):
        is_fraud = i % 2 == 1
        if is_fraud:
            handle = random.choice(["upi", "paytm", "ybl"])
            vpa = f"{random.choice(['refund', 'verify', 'support'])}{random.randint(1000,99999)}@{handle}"
            pn = random.choice(scam_names)
            tn = random.choice(["urgent refund verification", "claim cashback now", "kyc blocked account"])
            amount = random.choice([1, 99, 499, 999, 2499, 9999])
        else:
            handle = random.choice(TRUSTED_HANDLES)
            vpa = f"{random.choice(merchants)}@{handle}"
            pn = random.choice(merchants).title()
            tn = random.choice(["bill payment", "order payment", "subscription", "merchant payment"])
            amount = random.choice([50, 100, 249, 500, 1200, 3000])
        rows.append({
            "upi_string": f"upi://pay?pa={vpa}&pn={pn}&am={amount}&cu=INR&tn={tn}",
            "label_standardized": "fraud" if is_fraud else "safe",
            "label_binary": int(is_fraud),
        })
    return pd.DataFrame(rows)


class UPIModelTrainer:
    def __init__(self) -> None:
        self.extractor = UPIFeatureExtractor()

    def train(self, df: pd.DataFrame | None = None) -> dict:
        df = df if df is not None else generate_synthetic_upi()
        x = self.extractor.extract(df["upi_string"])
        y = df["label_binary"].astype(int)
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, stratify=y, random_state=settings.RANDOM_SEED
        )
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
        joblib.dump({"model": model, "features": list(x.columns)}, settings.ml_model_dir / "upi_model.pkl")
        return metrics
