"""
SurakshaAI — Label Mapper
==========================
Standardizes all dataset labels to exactly three values:
    safe    → legitimate communication
    fraud   → fraudulent communication
    unknown → no label or unrecognizable label

Rules:
  - Every label in LABEL_MAP is deterministically mapped.
  - Any label NOT in LABEL_MAP → unknown.
  - unknown records are logged and excluded from training.
  - unknown is NEVER silently converted to safe or fraud.

Usage:
    from src.preprocessing.label_mapper import LabelMapper
    mapper = LabelMapper()
    df = mapper.apply(df, label_col="v1")
    df_clean = mapper.drop_unknown(df)
    mapper.print_distribution(df)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ── Master Label Map ──────────────────────────────────────────────────────────
# All known raw label values → standardized label
# Keys are lowercased and stripped before lookup
LABEL_MAP: Dict[str, str] = {
    # Safe labels
    "ham":           "safe",
    "legit":         "safe",
    "legitimate":    "safe",
    "genuine":       "safe",
    "safe":          "safe",
    "benign":        "safe",
    "normal":        "safe",
    "not spam":      "safe",
    "not_spam":      "safe",
    "real":          "safe",
    "authentic":     "safe",
    "0":             "safe",    # numeric encoding

    # Fraud labels
    "spam":          "fraud",
    "scam":          "fraud",
    "fraud":         "fraud",
    "phishing":      "fraud",
    "smishing":      "fraud",
    "malicious":     "fraud",
    "defacement":    "fraud",
    "malware":       "fraud",
    "fake":          "fraud",
    "suspicious":    "fraud",
    "1":             "fraud",   # numeric encoding
    "yes":           "fraud",   # some datasets use yes/no
    "no":            "safe",

    # Email-specific
    "phishing email":  "fraud",
    "safe email":      "safe",
    "spam email":      "fraud",
    "email type":      "unknown",   # header row artifact

    # URL-specific
    "benign url":      "safe",
    "phishing url":    "fraud",
    "malware url":     "fraud",
    "defacement url":  "fraud",
}

# Canonical output labels
VALID_LABELS = {"safe", "fraud", "unknown"}

# Binary numeric map for model training
BINARY_MAP: Dict[str, int] = {
    "safe":  0,
    "fraud": 1,
}


class LabelMapper:
    """
    Maps raw dataset labels to the standardized safe / fraud / unknown schema.
    """

    def __init__(self, custom_map: Optional[Dict[str, str]] = None) -> None:
        """
        Args:
            custom_map: optional additional mappings to merge with LABEL_MAP.
                        custom_map takes precedence over defaults.
        """
        self.label_map = {**LABEL_MAP}
        if custom_map:
            self.label_map.update(
                {k.lower().strip(): v for k, v in custom_map.items()}
            )
        self._unmapped_seen: List[str] = []

    # ── Core Mapping ──────────────────────────────────────────────────────────
    def map_label(self, raw_label) -> str:
        """
        Map a single raw label value to safe, fraud, or unknown.

        Args:
            raw_label: any value from the original label column

        Returns:
            "safe" | "fraud" | "unknown"
        """
        if raw_label is None or (
            isinstance(raw_label, float) and pd.isna(raw_label)
        ):
            return "unknown"

        normalized = str(raw_label).lower().strip()

        if normalized in self.label_map:
            return self.label_map[normalized]

        # Track unmapped labels for reporting
        if normalized not in self._unmapped_seen:
            self._unmapped_seen.append(normalized)
            logger.warning(
                "Unmapped label '%s' → unknown. "
                "Add to LABEL_MAP if this label has a known meaning.",
                normalized,
            )

        return "unknown"

    def apply(
        self,
        df: pd.DataFrame,
        label_col: str,
        output_col: str = "label_standardized",
    ) -> pd.DataFrame:
        """
        Apply label mapping to an entire DataFrame column.

        Args:
            df         : input DataFrame
            label_col  : name of the raw label column
            output_col : name of the new standardized label column

        Returns:
            DataFrame with the new standardized label column added.
            The original label column is preserved as label_original.
        """
        df = df.copy()

        if label_col not in df.columns:
            logger.warning(
                "Label column '%s' not found. "
                "All records assigned label=unknown.",
                label_col,
            )
            df["label_original"]  = None
            df[output_col]        = "unknown"
            return df

        df["label_original"] = df[label_col].astype(str)
        df[output_col] = df[label_col].apply(self.map_label)

        # Summary
        dist = df[output_col].value_counts().to_dict()
        logger.info(
            "Label mapping complete: safe=%d  fraud=%d  unknown=%d",
            dist.get("safe", 0),
            dist.get("fraud", 0),
            dist.get("unknown", 0),
        )

        return df

    def apply_no_label(
        self,
        df: pd.DataFrame,
        output_col: str = "label_standardized",
    ) -> pd.DataFrame:
        """
        Apply to a DataFrame that has NO label column.
        All records are assigned unknown.

        Used for: Indian Banking SMS dataset if labels are absent.
        """
        df = df.copy()
        df["label_original"] = None
        df[output_col]       = "unknown"
        logger.warning(
            "No label column available. "
            "%d records assigned label=unknown and will be excluded from training.",
            len(df),
        )
        return df

    # ── Filtering ─────────────────────────────────────────────────────────────
    def drop_unknown(
        self,
        df: pd.DataFrame,
        label_col: str = "label_standardized",
    ) -> pd.DataFrame:
        """
        Remove all unknown records from the DataFrame.
        Logs how many records are dropped.

        Returns:
            DataFrame with only safe and fraud records.
        """
        before = len(df)
        df_clean = df[df[label_col].isin(["safe", "fraud"])].copy()
        after  = len(df_clean)
        dropped = before - after

        if dropped > 0:
            logger.info(
                "Dropped %d unknown records (%.1f%% of total).",
                dropped,
                100 * dropped / before,
            )

        return df_clean.reset_index(drop=True)

    def add_binary_label(
        self,
        df: pd.DataFrame,
        label_col: str = "label_standardized",
        output_col: str = "label_binary",
    ) -> pd.DataFrame:
        """
        Add a binary integer label column: safe=0, fraud=1.
        Unknown records will receive NaN — drop them before calling this.

        Args:
            df         : DataFrame with standardized labels
            label_col  : column containing safe/fraud/unknown
            output_col : name for the new binary column

        Returns:
            DataFrame with binary label column added.
        """
        df = df.copy()
        df[output_col] = df[label_col].map(BINARY_MAP)

        null_count = df[output_col].isna().sum()
        if null_count > 0:
            logger.warning(
                "%d records have NaN binary label "
                "(likely unknown records that were not dropped).",
                null_count,
            )

        return df

    # ── Reporting ─────────────────────────────────────────────────────────────
    def print_distribution(
        self,
        df: pd.DataFrame,
        label_col: str = "label_standardized",
        dataset_name: str = "",
    ) -> None:
        """Print label distribution to console."""
        dist = df[label_col].value_counts()
        total = len(df)

        header = f"Label Distribution — {dataset_name}" if dataset_name else "Label Distribution"
        print(f"\n  {header}")
        print(f"  {'─' * 40}")
        for label, count in dist.items():
            pct = round(100 * count / total, 1)
            bar = "█" * int(pct / 2)
            print(f"  {label:<10} {count:>8,}  ({pct:>5.1f}%)  {bar}")
        print(f"  {'─' * 40}")
        print(f"  {'Total':<10} {total:>8,}")

        if self._unmapped_seen:
            print(f"\n  ⚠️  Unmapped labels seen (mapped to unknown):")
            for u in self._unmapped_seen:
                print(f"       '{u}'")
        print()

    def get_unmapped_labels(self) -> List[str]:
        """Return list of label values that were not in LABEL_MAP."""
        return list(self._unmapped_seen)

    @staticmethod
    def validate_binary_only(
        df: pd.DataFrame,
        label_col: str = "label_standardized",
    ) -> bool:
        """
        Assert that a DataFrame contains only safe and fraud labels.
        Returns True if valid, False otherwise.
        Call this before any model training.
        """
        unique = set(df[label_col].unique())
        invalid = unique - {"safe", "fraud"}
        if invalid:
            logger.error(
                "Non-binary labels found in training data: %s. "
                "Remove unknown records before training.",
                invalid,
            )
            return False
        return True