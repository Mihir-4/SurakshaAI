"""
SurakshaAI — Dataset Validator
================================
Per-dataset validation pipeline.
Checks each raw dataset for:
  - Required columns (flexible: tries multiple known column names)
  - Null rates in critical columns
  - Label distribution
  - Text length distribution
  - Encoding correctness
  - Duplicate detection
  - Minimum row count

Produces a validation report dict for each dataset.
Does NOT clean or transform data — that is Module 2.

Usage:
    from src.data.validate import DatasetValidator
    validator = DatasetValidator()
    report = validator.validate("sms_spam", df)
    validator.print_report(report)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import settings

logger = logging.getLogger(__name__)


# ── Column name candidates per dataset ────────────────────────────────────────
# Maps dataset → (text_candidates, label_candidates)
COLUMN_CANDIDATES: Dict[str, Tuple[List[str], List[str]]] = {
    "financial_scams": (
        ["message", "text", "content", "sms", "msg"],
        ["label", "class", "category", "type"],
    ),
    "sms_phishing": (
        ["message", "text", "sms", "msg"],
        ["label", "class", "category"],
    ),
    "sms_spam": (
        ["v2", "message", "text", "sms"],
        ["v1", "label", "class"],
    ),
    "phishing_email": (
        ["body", "email_text", "text", "message", "content"],
        ["label", "class", "category", "Email Type"],
    ),
    "indian_banking_sms": (
        ["message", "text", "sms", "msg", "content"],
        ["label", "class", "category", "type"],
    ),
    "manual_banking": (
        ["text", "message", "content"],
        ["label"],
    ),
    "manual_loan": (
        ["text", "message", "content"],
        ["label"],
    ),
    "manual_whatsapp": (
        ["text", "message", "content"],
        ["label"],
    ),
    "urls": (
        ["url"],
        ["type", "label", "class"],
    ),
    "upi": (
        ["upi_string", "upi_uri", "text"],
        ["label", "class"],
    ),
}

# Minimum rows required to consider a dataset usable
MIN_ROWS: Dict[str, int] = {
    "financial_scams":    200,
    "sms_phishing":      2000,
    "sms_spam":          2000,
    "phishing_email":   10000,
    "indian_banking_sms": 500,
    "manual_banking":     50,
    "manual_loan":        50,
    "manual_whatsapp":    50,
    "urls":             5000,
    "upi":               500,
}


class DatasetValidator:
    """
    Validates raw DataFrames before any cleaning or transformation.
    """

    # ── Main Entry Point ──────────────────────────────────────────────────────
    def validate(
        self,
        dataset_name: str,
        df: pd.DataFrame,
    ) -> dict:
        """
        Run all validation checks on a raw DataFrame.

        Returns a report dict with keys:
            dataset_name, passed, errors, warnings,
            row_count, text_col, label_col,
            null_text_pct, null_label_pct,
            label_distribution, text_length_stats,
            duplicate_count, encoding_ok
        """
        report = {
            "dataset_name":      dataset_name,
            "passed":            True,
            "errors":            [],
            "warnings":          [],
            "row_count":         len(df),
            "col_count":         len(df.columns),
            "columns_found":     list(df.columns),
            "text_col":          None,
            "label_col":         None,
            "null_text_pct":     None,
            "null_label_pct":    None,
            "label_distribution": {},
            "text_length_stats": {},
            "duplicate_count":   0,
            "encoding_ok":       True,
        }

        # 1. Minimum rows
        self._check_min_rows(dataset_name, df, report)

        # 2. Identify text and label columns
        text_col  = self._find_column(df, dataset_name, "text")
        label_col = self._find_column(df, dataset_name, "label")

        report["text_col"]  = text_col
        report["label_col"] = label_col

        if text_col is None:
            report["errors"].append(
                f"No text column found. Tried: "
                f"{COLUMN_CANDIDATES.get(dataset_name, ([],[]))[0]}"
            )
            report["passed"] = False
            return report

        # 3. Null rates
        self._check_nulls(df, text_col, label_col, report)

        # 4. Text length stats
        self._check_text_lengths(df, text_col, report)

        # 5. Label distribution
        if label_col:
            self._check_labels(df, label_col, report)
        else:
            report["warnings"].append(
                "No label column found. "
                "Records will be assigned label=unknown and excluded from training."
            )

        # 6. Duplicates
        self._check_duplicates(df, text_col, report)

        # 7. Encoding
        self._check_encoding(df, text_col, report)

        # 8. Dataset-specific checks
        self._dataset_specific_checks(dataset_name, df, report)

        return report

    # ── Column Discovery ──────────────────────────────────────────────────────
    def _find_column(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        col_type: str,          # "text" or "label"
    ) -> Optional[str]:
        """
        Find the best matching column name in the DataFrame.
        col_type: "text" finds the message/content column
                  "label" finds the label/class column
        """
        candidates_map = COLUMN_CANDIDATES.get(dataset_name, ([], []))
        candidates = candidates_map[0] if col_type == "text" else candidates_map[1]

        # Exact match first
        for c in candidates:
            if c in df.columns:
                return c

        # Case-insensitive match
        lower_cols = {col.lower(): col for col in df.columns}
        for c in candidates:
            if c.lower() in lower_cols:
                return lower_cols[c.lower()]

        # Partial match as last resort
        for c in candidates:
            matches = [col for col in df.columns if c.lower() in col.lower()]
            if matches:
                return matches[0]

        return None

    # ── Individual Checks ─────────────────────────────────────────────────────
    def _check_min_rows(
        self,
        dataset_name: str,
        df: pd.DataFrame,
        report: dict,
    ) -> None:
        min_r = MIN_ROWS.get(dataset_name, 100)
        if len(df) < min_r:
            report["errors"].append(
                f"Row count {len(df)} is below minimum {min_r}"
            )
            report["passed"] = False
        elif len(df) < min_r * 2:
            report["warnings"].append(
                f"Row count {len(df)} is low (minimum is {min_r})"
            )

    def _check_nulls(
        self,
        df: pd.DataFrame,
        text_col: str,
        label_col: Optional[str],
        report: dict,
    ) -> None:
        null_text = df[text_col].isna().sum()
        null_text_pct = round(100 * null_text / len(df), 2)
        report["null_text_pct"] = null_text_pct

        if null_text_pct > 5.0:
            report["warnings"].append(
                f"{null_text_pct}% of text values are null"
            )
        if null_text_pct > 20.0:
            report["errors"].append(
                f"{null_text_pct}% null text — dataset may be corrupt"
            )
            report["passed"] = False

        if label_col:
            null_label = df[label_col].isna().sum()
            null_label_pct = round(100 * null_label / len(df), 2)
            report["null_label_pct"] = null_label_pct
            if null_label_pct > 10.0:
                report["warnings"].append(
                    f"{null_label_pct}% of labels are null"
                )

    def _check_text_lengths(
        self,
        df: pd.DataFrame,
        text_col: str,
        report: dict,
    ) -> None:
        lengths = df[text_col].dropna().astype(str).str.len()
        report["text_length_stats"] = {
            "min":    int(lengths.min()),
            "max":    int(lengths.max()),
            "mean":   round(float(lengths.mean()), 1),
            "median": round(float(lengths.median()), 1),
            "p95":    round(float(lengths.quantile(0.95)), 1),
        }
        very_short = (lengths < 5).sum()
        very_long  = (lengths > 20000).sum()
        if very_short > 0:
            report["warnings"].append(
                f"{very_short} records have text shorter than 5 characters"
            )
        if very_long > 0:
            report["warnings"].append(
                f"{very_long} records have text longer than 20,000 characters"
            )

    def _check_labels(
        self,
        df: pd.DataFrame,
        label_col: str,
        report: dict,
    ) -> None:
        dist = df[label_col].value_counts().to_dict()
        report["label_distribution"] = {
            str(k): int(v) for k, v in dist.items()
        }
        n_classes = len(dist)
        if n_classes == 0:
            report["errors"].append("Label column is entirely null")
            report["passed"] = False
        elif n_classes == 1:
            report["warnings"].append(
                f"Only one class found: {list(dist.keys())[0]}"
            )
        elif n_classes > 10:
            report["warnings"].append(
                f"{n_classes} distinct label values — "
                "verify label standardization is needed"
            )

    def _check_duplicates(
        self,
        df: pd.DataFrame,
        text_col: str,
        report: dict,
    ) -> None:
        dupes = df[text_col].dropna().duplicated().sum()
        report["duplicate_count"] = int(dupes)
        dupe_pct = round(100 * dupes / len(df), 2)
        if dupe_pct > 10.0:
            report["warnings"].append(
                f"{dupe_pct}% duplicate text values ({dupes} records)"
            )

    def _check_encoding(
        self,
        df: pd.DataFrame,
        text_col: str,
        report: dict,
    ) -> None:
        """Check for null bytes or control characters indicating encoding issues."""
        sample = df[text_col].dropna().astype(str).head(1000)
        null_byte_count = sample.str.contains("\x00").sum()
        if null_byte_count > 0:
            report["warnings"].append(
                f"{null_byte_count} records contain null bytes — "
                "possible encoding issue"
            )
            report["encoding_ok"] = False

    def _dataset_specific_checks(
        self,
        dataset_name: str,
        df: pd.DataFrame,
        report: dict,
    ) -> None:
        """Run checks specific to individual datasets."""

        # SMS Phishing: check for indicator columns
        if dataset_name == "sms_phishing":
            for col in ["url_present", "email_present", "phone_present"]:
                if col in df.columns:
                    report["warnings"] = [
                        w for w in report["warnings"]
                        if col not in w
                    ]
                else:
                    report["warnings"].append(
                        f"Optional indicator column '{col}' not found — "
                        "will set to 0 during feature engineering"
                    )

        # SMS Spam: check v1/v2 naming
        if dataset_name == "sms_spam":
            if "v1" in df.columns and "v2" in df.columns:
                pass  # correct format
            elif "label" in df.columns and "message" in df.columns:
                report["warnings"].append(
                    "sms_spam has non-standard column names (label/message). "
                    "Will be handled during cleaning."
                )

        # Indian Banking SMS: check for label column
        if dataset_name == "indian_banking_sms":
            has_label = any(
                c in df.columns
                for c in ["label", "class", "category", "type"]
            )
            if not has_label:
                report["warnings"].append(
                    "CRITICAL: indian_banking_sms has no label column. "
                    "All records will be assigned label=unknown and "
                    "excluded from supervised training."
                )

        # URL dataset: check for url and type columns
        if dataset_name == "urls":
            if "url" not in df.columns:
                report["errors"].append("URL dataset missing 'url' column")
                report["passed"] = False
            if "type" not in df.columns and "label" not in df.columns:
                report["errors"].append(
                    "URL dataset missing 'type' or 'label' column"
                )
                report["passed"] = False

        # Phishing email: check for subject + body
        if dataset_name == "phishing_email":
            has_body = any(
                c in df.columns
                for c in ["body", "email_text", "text", "message", "content"]
            )
            if not has_body:
                report["errors"].append(
                    "Phishing email dataset: no body column found"
                )
                report["passed"] = False

    # ── Reporting ─────────────────────────────────────────────────────────────
    def print_report(self, report: dict) -> None:
        """Print a human-readable validation report."""
        status = "PASSED ✅" if report["passed"] else "FAILED ❌"
        print(f"\n{'='*60}")
        print(f"  {report['dataset_name'].upper()} — Validation {status}")
        print(f"{'='*60}")
        print(f"  Rows      : {report['row_count']:,}")
        print(f"  Text col  : {report['text_col']}")
        print(f"  Label col : {report['label_col']}")
        print(f"  Null text : {report['null_text_pct']}%")
        print(f"  Nulllabel : {report['null_label_pct']}%")
        print(f"  Dupes     : {report['duplicate_count']:,}")

        if report["label_distribution"]:
            print(f"\n  Label Distribution:")
            for label, count in report["label_distribution"].items():
                pct = round(100 * count / report["row_count"], 1)
                print(f"    {label:<20} {count:>8,}  ({pct}%)")

        if report["text_length_stats"]:
            st = report["text_length_stats"]
            print(f"\n  Text Length:")
            print(f"    min={st['min']}  max={st['max']}  "
                  f"mean={st['mean']}  median={st['median']}  p95={st['p95']}")

        if report["errors"]:
            print(f"\n  Errors:")
            for e in report["errors"]:
                print(f"    ❌ {e}")

        if report["warnings"]:
            print(f"\n  Warnings:")
            for w in report["warnings"]:
                print(f"    ⚠️  {w}")

        print(f"{'='*60}\n")

    def validate_all(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> Dict[str, dict]:
        """
        Validate multiple datasets at once.

        Args:
            datasets: dict of dataset_name → DataFrame

        Returns:
            dict of dataset_name → validation report
        """
        reports = {}
        for name, df in datasets.items():
            logger.info("Validating %s...", name)
            reports[name] = self.validate(name, df)
        return reports

    def summary_dataframe(
        self,
        reports: Dict[str, dict],
    ) -> pd.DataFrame:
        """
        Convert all validation reports to a summary DataFrame.
        Useful for notebook display and CSV export.
        """
        rows = []
        for name, r in reports.items():
            rows.append({
                "dataset":        name,
                "passed":         r["passed"],
                "row_count":      r["row_count"],
                "text_col":       r["text_col"],
                "label_col":      r["label_col"],
                "null_text_pct":  r["null_text_pct"],
                "null_label_pct": r["null_label_pct"],
                "duplicate_count":r["duplicate_count"],
                "errors":         "; ".join(r["errors"]),
                "warnings":       "; ".join(r["warnings"]),
            })
        return pd.DataFrame(rows)