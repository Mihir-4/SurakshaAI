"""Classical ML training for the financial text classifier."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.config import settings
from src.preprocessing.feature_engineer import FeatureEngineer
from src.models.model_registry import ArtifactRegistry, ModelCard

logger = logging.getLogger(__name__)


def fraud_recall_at_fpr(y_true: Iterable[int], y_score: Iterable[float], max_fpr: float = 0.05) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    valid = np.where(fpr <= max_fpr)[0]
    return float(tpr[valid].max()) if len(valid) else 0.0


def binary_metrics(y_true: Iterable[int], y_pred: Iterable[int], y_score: Iterable[float]) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=[0, 1], zero_division=0
    )
    try:
        roc_auc = roc_auc_score(y_true, y_score)
    except ValueError:
        roc_auc = 0.0
    try:
        pr_auc = average_precision_score(y_true, y_score)
    except ValueError:
        pr_auc = 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "safe_precision": float(precision[0]),
        "safe_recall": float(recall[0]),
        "fraud_precision": float(precision[1]),
        "fraud_recall": float(recall[1]),
        "fraud_f1": float(f1[1]),
        "fraud_recall_5fpr": fraud_recall_at_fpr(y_true, y_score),
    }


class TextMLTrainer:
    """Trains TF-IDF plus engineered-feature sklearn models."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or settings.ml_model_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.feature_engineer = FeatureEngineer()

    def _build_features(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Tuple:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            max_features=80000,
            sublinear_tf=True,
        )
        x_train_text = vectorizer.fit_transform(train_df["cleaned_text"].fillna(""))
        x_val_text = vectorizer.transform(val_df["cleaned_text"].fillna(""))
        x_test_text = vectorizer.transform(test_df["cleaned_text"].fillna(""))

        train_num = self.feature_engineer.extract(train_df)
        val_num = self.feature_engineer.extract(val_df)
        test_num = self.feature_engineer.extract(test_df)

        scaler = StandardScaler(with_mean=False)
        x_train_num = scaler.fit_transform(train_num)
        x_val_num = scaler.transform(val_num)
        x_test_num = scaler.transform(test_num)

        feature_names = (
            list(vectorizer.get_feature_names_out())
            + [f"num__{name}" for name in train_num.columns]
        )

        return (
            hstack([x_train_text, x_train_num]),
            hstack([x_val_text, x_val_num]),
            hstack([x_test_text, x_test_num]),
            vectorizer,
            scaler,
            feature_names,
        )

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        version: str = "v1",
    ) -> pd.DataFrame:
        x_train, x_val, x_test, vectorizer, scaler, feature_names = self._build_features(
            train_df, val_df, test_df
        )
        y_train = train_df["label_binary"].astype(int).values
        y_val = val_df["label_binary"].astype(int).values
        y_test = test_df["label_binary"].astype(int).values

        candidates = {
            "logistic_regression": LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                n_jobs=-1,
                random_state=settings.RANDOM_SEED,
            ),
            "decision_tree": DecisionTreeClassifier(
                class_weight="balanced",
                max_depth=30,
                min_samples_leaf=5,
                random_state=settings.RANDOM_SEED,
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=250,
                class_weight="balanced_subsample",
                max_depth=None,
                min_samples_leaf=2,
                n_jobs=-1,
                random_state=settings.RANDOM_SEED,
            ),
        }

        try:
            from xgboost import XGBClassifier

            pos = max(int((y_train == 1).sum()), 1)
            neg = max(int((y_train == 0).sum()), 1)
            candidates["xgboost_text"] = XGBClassifier(
                n_estimators=400,
                max_depth=6,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="binary:logistic",
                eval_metric="logloss",
                scale_pos_weight=neg / pos,
                random_state=settings.RANDOM_SEED,
                n_jobs=-1,
            )
        except Exception as exc:
            logger.warning("XGBoost unavailable, skipping text XGBoost: %s", exc)

        rows = []
        best_name = None
        best_model = None
        best_score = -1.0

        for name, model in candidates.items():
            logger.info("Training %s", name)
            calibrated = CalibratedClassifierCV(model, method="sigmoid", cv=3)
            calibrated.fit(x_train, y_train)
            val_score = calibrated.predict_proba(x_val)[:, 1]
            val_pred = (val_score >= 0.5).astype(int)
            test_score = calibrated.predict_proba(x_test)[:, 1]
            test_pred = (test_score >= 0.5).astype(int)

            val_metrics = binary_metrics(y_val, val_pred, val_score)
            test_metrics = binary_metrics(y_test, test_pred, test_score)
            rows.append({
                "model_name": name,
                **{f"val_{k}": v for k, v in val_metrics.items()},
                **{f"test_{k}": v for k, v in test_metrics.items()},
            })

            joblib.dump(calibrated, self.output_dir / f"{name}.pkl")
            if val_metrics["f1_macro"] > best_score:
                best_name = name
                best_model = calibrated
                best_score = val_metrics["f1_macro"]

        joblib.dump(vectorizer, self.output_dir / "tfidf_vectorizer.pkl")
        joblib.dump(scaler, self.output_dir / "feature_scaler.pkl")
        (self.output_dir / "feature_names.json").write_text(
            json.dumps(feature_names, indent=2),
            encoding="utf-8",
        )
        joblib.dump(best_model, self.output_dir / "best_text_ml.pkl")

        comparison = pd.DataFrame(rows).sort_values("val_f1_macro", ascending=False)
        settings.reports_dir.mkdir(parents=True, exist_ok=True)
        comparison.to_csv(settings.reports_dir / "module3_ml_comparison.csv", index=False)

        best_row = comparison.iloc[0].to_dict()
        ArtifactRegistry().register(
            ModelCard(
                model_name=str(best_name),
                model_type="ml",
                version=version,
                artifact_path=str(self.output_dir / "best_text_ml.pkl"),
                metrics={k: float(v) for k, v in best_row.items() if k.startswith("test_")},
                hyperparameters={"tfidf_max_features": 80000, "calibration": "sigmoid"},
                calibration_method="platt_scaling",
                notes=f"train={len(train_df)}, val={len(val_df)}, test={len(test_df)}",
            )
        )
        return comparison


def train_from_processed(processed_dir: Path | None = None) -> pd.DataFrame:
    processed_dir = processed_dir or settings.processed_data_dir
    train_df = pd.read_csv(processed_dir / "text_train.csv")
    val_df = pd.read_csv(processed_dir / "text_val.csv")
    test_df = pd.read_csv(processed_dir / "text_test.csv")
    return TextMLTrainer().train(train_df, val_df, test_df)
