"""
SurakshaAI — Dataset Download Helpers
=======================================
Provides utilities for:
  - Verifying datasets are present in data/raw/
  - Finding the primary CSV file inside a dataset folder
  - Computing file checksums for integrity verification
  - Printing a download status report

NOTE: This module does NOT download files automatically.
Kaggle datasets must be downloaded via the Kaggle API CLI.
Mendeley datasets must be downloaded manually via browser.
This module validates what is already present.

Usage (in Module 1 notebook):
    from src.data.download import DatasetDownloadManager
    manager = DatasetDownloadManager()
    manager.verify_all()
    manager.print_status_report()
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.config import settings

logger = logging.getLogger(__name__)


# ── Expected files per dataset ────────────────────────────────────────────────
# Maps dataset_name → list of candidate filenames to look for.
# The first file found in the folder that matches any candidate is used.
EXPECTED_FILES: Dict[str, List[str]] = {
    "financial_scams": [
        "financial_scams.csv",
        "Financial Scam.csv",
        "scam_messages.csv",
        "data.csv",
        "dataset.csv",
    ],
    "sms_phishing": [
        "sms_phishing.csv",
        "Dataset.csv",
        "dataset.csv",
        "phishing_sms.csv",
        "data.csv",
    ],
    "sms_spam": [
        "spam.csv",
        "SMSSpamCollection",
        "sms_spam.csv",
        "data.csv",
    ],
    "phishing_email": [
        "phishing_email.csv",
        "Phishing_Email.csv",
        "emails.csv",
        "data.csv",
        "dataset.csv",
    ],
    "indian_banking_sms": [
        "sms_data.csv",
        "SMS_data.csv",
        "indian_sms.csv",
        "data.csv",
        "sms.csv",
    ],
    "manual_banking": [
        "banking_notifications.csv",
        "manual_banking.csv",
    ],
    "manual_loan": [
        "loan_advertisements.csv",
        "manual_loan.csv",
    ],
    "manual_whatsapp": [
        "whatsapp_chats.csv",
        "manual_whatsapp.csv",
    ],
    "urls": [
        "malicious_urls.csv",
        "url_dataset.csv",
        "URLs.csv",
        "data.csv",
        "url.csv",
        "urldata.csv",
    ],
    "upi": [
        "upi_dataset.csv",
        "upi_synthetic.csv",
        "upi.csv",
    ],
}

# Minimum expected row counts per dataset (for validation warning)
MIN_EXPECTED_ROWS: Dict[str, int] = {
    "financial_scams":    400,
    "sms_phishing":      5000,
    "sms_spam":          5000,
    "phishing_email":   50000,
    "indian_banking_sms": 1000,
    "manual_banking":      100,
    "manual_loan":         100,
    "manual_whatsapp":     100,
    "urls":             100000,
    "upi":               1000,
}


class DatasetDownloadManager:
    """
    Verifies presence and basic integrity of all raw datasets.
    Does not download; validates what exists.
    """

    def __init__(self) -> None:
        self.raw_dir = settings.raw_data_dir
        self.status: Dict[str, dict] = {}

    # ── Core Verification ─────────────────────────────────────────────────────
    def verify_all(self) -> Dict[str, dict]:
        """
        Verify all datasets.
        Returns a dict of dataset_name → status dict.
        """
        for name in EXPECTED_FILES:
            self.status[name] = self._verify_one(name)
        return self.status

    def _verify_one(self, dataset_name: str) -> dict:
        """
        Check a single dataset folder.
        Returns a status dict with keys:
          found, file_path, row_count, file_size_mb, checksum, error
        """
        folder = self.raw_dir / dataset_name
        result = {
            "dataset_name": dataset_name,
            "found":        False,
            "file_path":    None,
            "row_count":    0,
            "file_size_mb": 0.0,
            "checksum":     None,
            "error":        None,
            "warning":      None,
        }

        # ── Folder exists? ────────────────────────────────────────────────────
        if not folder.exists():
            result["error"] = f"Folder not found: {folder}"
            return result

        # ── Find primary file ─────────────────────────────────────────────────
        file_path = self._find_primary_file(folder, dataset_name)
        if file_path is None:
            # Fall back: use the first CSV found anywhere in the folder
            csvs = list(folder.rglob("*.csv"))
            if csvs:
                file_path = csvs[0]
            else:
                result["error"] = f"No CSV file found in {folder}"
                return result

        result["file_path"] = str(file_path)
        result["found"]     = True

        # ── File size ─────────────────────────────────────────────────────────
        size_bytes = file_path.stat().st_size
        result["file_size_mb"] = round(size_bytes / (1024 * 1024), 2)

        # ── Row count ─────────────────────────────────────────────────────────
        try:
            # Try common encodings
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, nrows=None)
                    result["row_count"] = len(df)
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    result["error"] = f"Could not read file: {e}"
                    return result
        except Exception as e:
            result["error"] = str(e)
            return result

        # ── Minimum rows check ────────────────────────────────────────────────
        min_rows = MIN_EXPECTED_ROWS.get(dataset_name, 0)
        if result["row_count"] < min_rows:
            result["warning"] = (
                f"Row count {result['row_count']} is below "
                f"expected minimum {min_rows}"
            )

        # ── Checksum ──────────────────────────────────────────────────────────
        result["checksum"] = self._compute_checksum(file_path)

        return result

    def _find_primary_file(
        self,
        folder: Path,
        dataset_name: str
    ) -> Optional[Path]:
        """
        Look for known candidate filenames in the dataset folder.
        Returns the first match found, or None.
        """
        candidates = EXPECTED_FILES.get(dataset_name, [])
        for candidate in candidates:
            path = folder / candidate
            if path.exists():
                return path
        return None

    # ── Checksum ──────────────────────────────────────────────────────────────
    @staticmethod
    def _compute_checksum(file_path: Path) -> str:
        """Compute SHA-256 of a file for integrity tracking."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    # ── Reporting ─────────────────────────────────────────────────────────────
    def print_status_report(self) -> None:
        """Print a colour-coded console report of all dataset statuses."""
        if not self.status:
            self.verify_all()

        print("\n" + "=" * 75)
        print(f"{'SurakshaAI — Dataset Download Status':^75}")
        print("=" * 75)

        all_ok   = True
        warnings = []

        for name, s in self.status.items():
            if s["found"] and s["error"] is None:
                icon = "✅"
                line = (
                    f"  {icon} {name:<25} "
                    f"{s['row_count']:>8,} rows  "
                    f"{s['file_size_mb']:>7.2f} MB"
                )
            else:
                icon    = "❌"
                all_ok  = False
                line    = f"  {icon} {name:<25} ERROR: {s['error']}"

            print(line)

            if s.get("warning"):
                warnings.append(f"  ⚠️  {name}: {s['warning']}")

        if warnings:
            print("\n  Warnings:")
            for w in warnings:
                print(w)

        print("\n" + "-" * 75)
        total   = len(self.status)
        found   = sum(1 for s in self.status.values() if s["found"])
        missing = total - found
        print(f"  Total: {total}  |  Found: {found}  |  Missing: {missing}")

        if all_ok and not warnings:
            print("  Status: ALL DATASETS PRESENT ✅")
        elif missing > 0:
            print(f"  Status: {missing} DATASET(S) MISSING ❌")
        else:
            print("  Status: ALL FOUND (with warnings) ⚠️")

        print("=" * 75 + "\n")

    def to_dataframe(self) -> pd.DataFrame:
        """Return status as a pandas DataFrame for notebook display."""
        if not self.status:
            self.verify_all()
        return pd.DataFrame(list(self.status.values()))

    # ── Individual dataset loaders ────────────────────────────────────────────
    def load_dataset(
        self,
        dataset_name: str,
        encoding: str = "utf-8",
        nrows: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Load a raw dataset into a DataFrame.
        Tries utf-8 first, falls back to latin-1.

        Args:
            dataset_name : one of the 10 dataset names
            encoding     : starting encoding to try
            nrows        : limit rows (useful for quick inspection)

        Returns:
            pd.DataFrame of the raw file

        Raises:
            FileNotFoundError if dataset folder or CSV not found
        """
        folder = self.raw_dir / dataset_name
        if not folder.exists():
            raise FileNotFoundError(
                f"Dataset folder not found: {folder}\n"
                f"Please download {dataset_name} first."
            )

        file_path = self._find_primary_file(folder, dataset_name)
        if file_path is None:
            csvs = list(folder.rglob("*.csv"))
            if not csvs:
                raise FileNotFoundError(
                    f"No CSV found in {folder}"
                )
            file_path = csvs[0]

        for enc in [encoding, "utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=enc, nrows=nrows)
                logger.info(
                    "Loaded %s: %d rows, %d cols [encoding=%s]",
                    dataset_name, len(df), len(df.columns), enc,
                )
                return df
            except UnicodeDecodeError:
                continue

        raise ValueError(f"Could not decode {file_path} with any known encoding.")

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """
        Load all available datasets into a dict.
        Skips any dataset that is not found.

        Returns:
            dict of dataset_name → DataFrame
        """
        loaded = {}
        for name in EXPECTED_FILES:
            try:
                loaded[name] = self.load_dataset(name)
            except FileNotFoundError as e:
                logger.warning("Skipping %s: %s", name, e)
        return loaded

    # ── Download Instructions ─────────────────────────────────────────────────
    def print_download_instructions(self) -> None:
        """
        Print manual download instructions for any missing datasets.
        """
        if not self.status:
            self.verify_all()

        missing = [
            name for name, s in self.status.items()
            if not s["found"]
        ]

        if not missing:
            print("All datasets are present. No downloads needed.")
            return

        print("\n" + "=" * 70)
        print("MISSING DATASETS — Download Instructions")
        print("=" * 70)

        kaggle_missing  = []
        mendeley_missing = []

        for name in missing:
            meta = EXPECTED_FILES.get(name, {})
            from src.data.catalog import DATASET_METADATA
            src = DATASET_METADATA.get(name, {}).get("source", "unknown")
            if src == "kaggle":
                kaggle_missing.append(name)
            elif src == "mendeley":
                mendeley_missing.append(name)

        if kaggle_missing:
            print("\nKaggle datasets (use Kaggle API):")
            kaggle_cmds = {
                "sms_spam":           "kaggle datasets download -d uciml/sms-spam-collection-dataset",
                "phishing_email":     "kaggle datasets download -d naserabdullahalam/phishing-email-dataset",
                "indian_banking_sms": "kaggle datasets download -d dshah1612/sms-data",
                "urls":               "kaggle datasets download -d sid321axn/malicious-urls-dataset",
            }
            for name in kaggle_missing:
                cmd = kaggle_cmds.get(name, f"# kaggle download for {name}")
                folder = f"data/raw/{name}"
                print(f"\n  {name}:")
                print(f"    {cmd} -p {folder} --unzip")

        if mendeley_missing:
            print("\nMendeley datasets (manual browser download):")
            mendeley_urls = {
                "financial_scams": "https://data.mendeley.com/datasets/znsk27yk3h/1",
                "sms_phishing":    "https://data.mendeley.com/datasets/f45bkkt8pr/1",
            }
            for name in mendeley_missing:
                url = mendeley_urls.get(name, "# see documentation")
                print(f"\n  {name}:")
                print(f"    URL: {url}")
                print(f"    → Place downloaded CSV in: data/raw/{name}/")

        print("\n" + "=" * 70 + "\n")