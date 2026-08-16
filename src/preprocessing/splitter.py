"""
SurakshaAI — Data Splitter
============================
Implements the correct data splitting pipeline:

  ORIGINAL RECORDS
       ↓
  Stratified 70/15/15 split (by source, then combined)
       ↓
  Lock val and test splits immediately
       ↓
  Augment train split only
       ↓
  Balance train split only

Guarantees:
  - Val and test contain ONLY original unmodified records
  - Augmented records NEVER appear in val or test
  - All records from one source are proportionally distributed
  - Stratification preserves safe/fraud ratio in every split
  - Random seed is fixed at settings.RANDOM_SEED for reproducibility

Usage:
    from src.preprocessing.splitter import DataSplitter
    splitter = DataSplitter()
    train_df, val_df, test_df = splitter.split(df)
    splitter.print_split_summary(train_df, val_df, test_df)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from src.config import settings

logger = logging.getLogger(__name__)


class DataSplitter:
    """
    Stratified grouped train/val/test splitter.
    Ensures no data source dominates any single split.
    """

    def __init__(
        self,
        train_ratio: float = settings.TRAIN_SPLIT,
        val_ratio:   float = settings.VAL_SPLIT,
        test_ratio:  float = settings.TEST_SPLIT,
        random_seed: int   = settings.RANDOM_SEED,
    ) -> None:
        """
        Args:
            train_ratio : fraction for training (default 0.70)
            val_ratio   : fraction for validation (default 0.15)
            test_ratio  : fraction for test (default 0.15)
            random_seed : fixed seed for reproducibility
        """
        total = train_ratio + val_ratio + test_ratio
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total:.3f}"
            )

        self.train_ratio = train_ratio
        self.val_ratio   = val_ratio
        self.test_ratio  = test_ratio
        self.random_seed = random_seed

    # ── Main Split Method ─────────────────────────────────────────────────────
    def split(
        self,
        df: pd.DataFrame,
        label_col:   str = "label_standardized",
        dataset_col: str = "dataset_name",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split a DataFrame into train, val, test sets.

        Strategy:
          1. Split per source dataset to ensure proportional representation
          2. Combine all per-source splits
          3. Shuffle the combined splits

        Args:
            df          : full cleaned DataFrame with original records only
            label_col   : binary label column (safe/fraud)
            dataset_col : source dataset column for grouping

        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        # Validate: only safe and fraud labels
        unique_labels = set(df[label_col].unique())
        invalid = unique_labels - {"safe", "fraud"}
        if invalid:
            raise ValueError(
                f"DataFrame contains non-binary labels: {invalid}. "
                "Run label_mapper.drop_unknown() before splitting."
            )

        train_parts = []
        val_parts   = []
        test_parts  = []

        if dataset_col in df.columns:
            # Split per source dataset
            for source_name, source_df in df.groupby(dataset_col):
                t, v, te = self._split_one(source_df, label_col, source_name)
                train_parts.append(t)
                val_parts.append(v)
                test_parts.append(te)
        else:
            # Single source: split directly
            t, v, te = self._split_one(df, label_col, "all")
            train_parts.append(t)
            val_parts.append(v)
            test_parts.append(te)

        train_df = self._combine_and_shuffle(train_parts, "train")
        val_df   = self._combine_and_shuffle(val_parts,   "val")
        test_df  = self._combine_and_shuffle(test_parts,  "test")

        # Mark split assignment
        train_df["split_assignment"] = "train"
        val_df["split_assignment"]   = "val"
        test_df["split_assignment"]  = "test"

        self._log_split_sizes(train_df, val_df, test_df, label_col)

        return train_df, val_df, test_df

    def _split_one(
        self,
        df: pd.DataFrame,
        label_col: str,
        source_name: str,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split a single-source DataFrame.
        If < 20 records, all go to train (too small to split).
        """
        if len(df) < 20:
            logger.warning(
                "Source '%s' has only %d records — all placed in train.",
                source_name, len(df),
            )
            return df.copy(), pd.DataFrame(columns=df.columns), pd.DataFrame(columns=df.columns)

        labels = df[label_col].values

        # First split: separate test set
        test_size = self.test_ratio
        val_size  = self.val_ratio / (self.train_ratio + self.val_ratio)

        try:
            train_val, test = train_test_split(
                df,
                test_size=test_size,
                stratify=labels,
                random_state=self.random_seed,
            )

            train, val = train_test_split(
                train_val,
                test_size=val_size,
                stratify=train_val[label_col].values,
                random_state=self.random_seed,
            )

        except ValueError as e:
            # Stratification fails when a class has too few members
            logger.warning(
                "Stratified split failed for '%s' (%s). "
                "Using non-stratified split.",
                source_name, e,
            )
            train_val, test = train_test_split(
                df,
                test_size=test_size,
                random_state=self.random_seed,
            )
            train, val = train_test_split(
                train_val,
                test_size=val_size,
                random_state=self.random_seed,
            )

        return train, val, test

    def _combine_and_shuffle(
        self,
        parts: list,
        split_name: str,
    ) -> pd.DataFrame:
        """Concatenate per-source splits and shuffle."""
        non_empty = [p for p in parts if len(p) > 0]
        if not non_empty:
            return pd.DataFrame()

        combined = pd.concat(non_empty, ignore_index=True)
        combined = combined.sample(
            frac=1,
            random_state=self.random_seed,
        ).reset_index(drop=True)

        logger.info("Split '%s': %d records", split_name, len(combined))
        return combined

    # ── Saving and Loading ────────────────────────────────────────────────────
    def save_splits(
        self,
        train_df: pd.DataFrame,
        val_df:   pd.DataFrame,
        test_df:  pd.DataFrame,
        output_dir: Optional[str] = None,
        prefix: str = "",
    ) -> dict:
        """
        Save all three splits to CSV.

        Args:
            train_df   : training split
            val_df     : validation split
            test_df    : test split
            output_dir : directory to save into (default: processed data dir)
            prefix     : optional filename prefix (e.g. "text_" or "url_")

        Returns:
            dict of split_name → file path
        """
        out_dir = Path(output_dir) if output_dir else settings.processed_data_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        paths = {}
        for split_name, split_df in [
            ("train_original", train_df),
            ("val_original",   val_df),
            ("test_original",  test_df),
        ]:
            filename = f"{prefix}{split_name}.csv" if prefix else f"{split_name}.csv"
            path     = out_dir / filename
            split_df.to_csv(path, index=False, encoding="utf-8")
            paths[split_name] = str(path)
            logger.info("Saved %s → %s (%d rows)", split_name, path, len(split_df))

        return paths

    @staticmethod
    def load_splits(
        processed_dir: Optional[str] = None,
        prefix: str = "",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load previously saved train/val/test splits.

        Args:
            processed_dir : directory containing split CSVs
            prefix        : filename prefix used when saving

        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        out_dir = (
            Path(processed_dir) if processed_dir
            else settings.processed_data_dir
        )

        splits = {}
        for split_name in ["train_original", "val_original", "test_original"]:
            filename = f"{prefix}{split_name}.csv" if prefix else f"{split_name}.csv"
            path     = out_dir / filename
            if not path.exists():
                raise FileNotFoundError(
                    f"Split file not found: {path}. "
                    "Run the preprocessing pipeline first."
                )
            splits[split_name] = pd.read_csv(path)
            logger.info("Loaded %s: %d rows", split_name, len(splits[split_name]))

        return (
            splits["train_original"],
            splits["val_original"],
            splits["test_original"],
        )

    # ── Class Balancing ───────────────────────────────────────────────────────
    def balance_training_split(
        self,
        train_df: pd.DataFrame,
        label_col: str = "label_standardized",
        target_ratio: float = 2.0,
        method: str = "undersample",
    ) -> pd.DataFrame:
        """
        Balance the training split class distribution.
        Applied ONLY to training split, never to val or test.

        Args:
            train_df     : augmented training split
            label_col    : label column
            target_ratio : max allowed majority/minority ratio (default 2:1)
            method       : "undersample" | "oversample"

        Returns:
            Balanced training DataFrame.
        """
        counts = train_df[label_col].value_counts()
        majority_label = counts.index[0]
        minority_label = counts.index[1]
        majority_count = counts.iloc[0]
        minority_count = counts.iloc[1]
        current_ratio  = majority_count / minority_count

        logger.info(
            "Before balancing: %s=%d, %s=%d, ratio=%.2f",
            majority_label, majority_count,
            minority_label, minority_count,
            current_ratio,
        )

        if current_ratio <= target_ratio:
            logger.info(
                "Ratio %.2f is within target %.2f — no balancing needed.",
                current_ratio, target_ratio,
            )
            return train_df

        majority_df = train_df[train_df[label_col] == majority_label]
        minority_df = train_df[train_df[label_col] == minority_label]

        if method == "undersample":
            target_majority = int(minority_count * target_ratio)
            majority_df = majority_df.sample(
                n=target_majority,
                random_state=self.random_seed,
            )

        elif method == "oversample":
            target_minority = int(majority_count / target_ratio)
            minority_df = minority_df.sample(
                n=target_minority,
                replace=True,
                random_state=self.random_seed,
            )

        balanced = pd.concat(
            [majority_df, minority_df], ignore_index=True
        ).sample(frac=1, random_state=self.random_seed).reset_index(drop=True)

        new_counts = balanced[label_col].value_counts()
        logger.info(
            "After balancing: %s=%d, %s=%d, ratio=%.2f",
            majority_label, new_counts.get(majority_label, 0),
            minority_label, new_counts.get(minority_label, 0),
            new_counts.iloc[0] / new_counts.iloc[1],
        )

        return balanced

    # ── Reporting ─────────────────────────────────────────────────────────────
    def print_split_summary(
        self,
        train_df: pd.DataFrame,
        val_df:   pd.DataFrame,
        test_df:  pd.DataFrame,
        label_col: str = "label_standardized",
    ) -> None:
        """Print a formatted split summary table."""
        total = len(train_df) + len(val_df) + len(test_df)

        print("\n  Data Split Summary")
        print("  " + "─" * 55)
        print(f"  {'Split':<10} {'Total':>8} {'%':>6} {'Safe':>8} {'Fraud':>8}")
        print("  " + "─" * 55)

        for name, df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
            if len(df) == 0:
                continue
            n      = len(df)
            pct    = round(100 * n / total, 1)
            safe   = (df[label_col] == "safe").sum()  if label_col in df.columns else "-"
            fraud  = (df[label_col] == "fraud").sum() if label_col in df.columns else "-"
            print(f"  {name:<10} {n:>8,} {pct:>5.1f}% {safe:>8,} {fraud:>8,}")

        print("  " + "─" * 55)
        print(f"  {'Total':<10} {total:>8,}")
        print()

    def _log_split_sizes(
        self,
        train_df: pd.DataFrame,
        val_df:   pd.DataFrame,
        test_df:  pd.DataFrame,
        label_col: str,
    ) -> None:
        total = len(train_df) + len(val_df) + len(test_df)
        logger.info(
            "Split complete — Train: %d (%.0f%%), "
            "Val: %d (%.0f%%), Test: %d (%.0f%%)",
            len(train_df), 100 * len(train_df) / total,
            len(val_df),   100 * len(val_df)   / total,
            len(test_df),  100 * len(test_df)  / total,
        )