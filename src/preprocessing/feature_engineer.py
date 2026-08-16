"""
SurakshaAI — Feature Engineer
==============================
Extracts hand-crafted features from cleaned financial text.
These features are combined with TF-IDF vectors for classical ML models.

Features extracted:
  Text statistics:
    message_length, word_count, avg_word_length,
    sentence_count, caps_ratio, digit_ratio, exclamation_count

  Entity presence (from token replacement):
    url_count, phone_count, has_otp_token, has_amount_token,
    has_account_token, has_upi_token, has_card_token

  Fraud signal keywords:
    has_urgency_keyword, has_money_keyword, has_bank_name,
    has_prize_keyword, has_credential_request,
    has_upfront_fee, has_suspicious_domain

  Optional (from SMS phishing dataset):
    url_present, email_present, phone_present

Usage:
    from src.preprocessing.feature_engineer import FeatureEngineer
    fe = FeatureEngineer()
    features_df = fe.extract(df, text_col="cleaned_text")
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Keyword Lists ─────────────────────────────────────────────────────────────

URGENCY_KEYWORDS = [
    "urgent", "urgently", "immediately", "expire", "expiry", "expires",
    "block", "blocked", "suspend", "suspended", "deactivate", "deactivated",
    "today", "24 hours", "24hrs", "last warning", "final notice",
    "action required", "act now", "do not ignore", "account will be",
    "will be closed", "will be blocked",
]

MONEY_KEYWORDS = [
    "rupees", "rs.", "rs ", "inr", "₹", "lakh", "crore",
    "cashback", "refund", "reward", "bonus", "prize money",
    "cash prize", "winning amount",
]

BANK_NAMES = [
    "sbi", "state bank", "hdfc", "icici", "axis bank", "bank of baroda",
    "bob", "pnb", "punjab national", "kotak", "yes bank", "canara",
    "union bank", "idbi", "indian bank", "central bank", "uco bank",
    "federal bank", "south indian bank", "karnataka bank", "rbl bank",
    "paytm", "phonepe", "gpay", "google pay", "bhim", "npci", "rbi",
]

PRIZE_KEYWORDS = [
    "won", "winner", "prize", "lottery", "lucky draw", "selected",
    "congratulations", "guaranteed cashback", "free gift", "reward",
    "you have been chosen", "claim your", "exclusive offer",
    "100% guaranteed", "get rich", "make money",
]

CREDENTIAL_KEYWORDS = [
    "password", "pin", "cvv", "card number", "card no", "otp",
    "share your", "provide your", "enter your", "verify your",
    "confirm your", "atm pin", "net banking password",
    "internet banking", "user id", "username",
]

UPFRONT_FEE_KEYWORDS = [
    "processing fee", "registration fee", "advance fee", "activation fee",
    "insurance fee", "security deposit", "admin fee", "handling charge",
    "pay first", "payment required", "fee required", "nominal fee",
    "small fee", "refundable deposit", "token amount",
]

SUSPICIOUS_DOMAIN_PATTERNS = [
    "URL_TOKEN",        # URL was tokenized (any URL in message is a signal)
    "secure-",
    "verify-",
    "update-",
    "login-",
    "-bank",
    "-sbi",
    "-hdfc",
    "-icici",
    ".xyz",
    ".tk",
    ".ml",
    ".cf",
    ".gq",
    ".top",
    ".pw",
]


class FeatureEngineer:
    """
    Extracts hand-crafted features from cleaned financial text.
    Works on cleaned text (after TextCleaner has been applied).
    """

    def __init__(self) -> None:
        # Pre-compile keyword patterns for efficiency
        self._urgency_re  = self._compile_keywords(URGENCY_KEYWORDS)
        self._money_re    = self._compile_keywords(MONEY_KEYWORDS)
        self._bank_re     = self._compile_keywords(BANK_NAMES)
        self._prize_re    = self._compile_keywords(PRIZE_KEYWORDS)
        self._cred_re     = self._compile_keywords(CREDENTIAL_KEYWORDS)
        self._fee_re      = self._compile_keywords(UPFRONT_FEE_KEYWORDS)

    # ── Public API ────────────────────────────────────────────────────────────
    def extract(
        self,
        df: pd.DataFrame,
        text_col: str = "cleaned_text",
        original_text_col: Optional[str] = "original_text",
    ) -> pd.DataFrame:
        """
        Extract all hand-crafted features from a DataFrame.

        Args:
            df               : DataFrame with cleaned text
            text_col         : column containing cleaned (lowercased) text
            original_text_col: column with original case text (for caps_ratio)

        Returns:
            DataFrame of features only (same index as input df).
            Concatenate with df to get the full feature set.
        """
        features = []

        for idx, row in df.iterrows():
            cleaned   = str(row.get(text_col, ""))
            original  = str(row.get(original_text_col, cleaned))

            feat = self._extract_one(cleaned, original, row)
            features.append(feat)

        feat_df = pd.DataFrame(features, index=df.index)
        logger.info(
            "Feature engineering complete: %d records × %d features",
            len(feat_df), len(feat_df.columns),
        )
        return feat_df

    def extract_one(
        self,
        text: str,
        original_text: Optional[str] = None,
    ) -> dict:
        """
        Extract features from a single text string.
        Used at inference time.

        Args:
            text          : cleaned lowercased text
            original_text : original case text (for caps_ratio)

        Returns:
            dict of feature_name → value
        """
        return self._extract_one(text, original_text or text, {})

    # ── Internal ──────────────────────────────────────────────────────────────
    def _extract_one(
        self,
        cleaned: str,
        original: str,
        row: dict,
    ) -> dict:
        """Extract all features for a single record."""

        words     = cleaned.split()
        sentences = re.split(r"[.!?]+", cleaned)

        # ── Text Statistics ───────────────────────────────────────────────────
        message_length  = len(cleaned)
        word_count      = len(words)
        avg_word_length = (
            np.mean([len(w) for w in words]) if words else 0.0
        )
        sentence_count = len([s for s in sentences if s.strip()])

        # caps_ratio computed on ORIGINAL text
        alpha_chars = [c for c in original if c.isalpha()]
        caps_ratio  = (
            sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if alpha_chars else 0.0
        )

        digit_chars  = [c for c in cleaned if c.isdigit()]
        digit_ratio  = len(digit_chars) / max(len(cleaned), 1)

        exclamation_count = original.count("!")
        question_count    = original.count("?")

        # ── Entity Tokens ─────────────────────────────────────────────────────
        url_count     = cleaned.count("url_token")
        phone_count   = cleaned.count("phone_token")
        has_otp_token = int("otp_token"     in cleaned)
        has_amount    = int("amount_token"  in cleaned)
        has_account   = int("account_token" in cleaned)
        has_upi       = int("upi_token"     in cleaned)
        has_card      = int("card_token"    in cleaned)
        has_ifsc      = int("ifsc_token"    in cleaned)

        # ── Keyword Signals ───────────────────────────────────────────────────
        has_urgency    = int(bool(self._urgency_re.search(cleaned)))
        has_money      = int(bool(self._money_re.search(cleaned)))
        has_bank_name  = int(bool(self._bank_re.search(cleaned)))
        has_prize      = int(bool(self._prize_re.search(cleaned)))
        has_credential = int(bool(self._cred_re.search(cleaned)))
        has_upfront    = int(bool(self._fee_re.search(cleaned)))

        # Suspicious domain: URL token present + suspicious keyword in original
        has_suspicious_domain = int(
            url_count > 0 and any(
                p.lower() in cleaned for p in SUSPICIOUS_DOMAIN_PATTERNS[1:]
            )
        )

        # ── Composite Signals ─────────────────────────────────────────────────
        # OTP request: credential request + otp keyword together
        has_otp_request = int(
            has_credential == 1 and (
                "otp" in cleaned or
                "one time" in cleaned or
                has_otp_token == 1
            )
        )

        # Bank impersonation: bank name + suspicious URL
        bank_with_suspicious_url = int(
            has_bank_name == 1 and url_count > 0
        )

        # Multiple urgency signals
        urgency_intensity = min(
            has_urgency + (exclamation_count > 2) + (caps_ratio > 0.3), 3
        )

        # ── Optional SMS Phishing Indicator Columns ───────────────────────────
        # These come from the Mendeley SMS phishing dataset
        url_present = self._safe_binary(
            row.get("url_present", None),
            default=url_count > 0,
        )
        email_present = self._safe_binary(
            row.get("email_present", None),
            default="@" in cleaned and url_count == 0,
        )
        phone_present = self._safe_binary(
            row.get("phone_present", None),
            default=phone_count > 0,
        )

        return {
            # Text statistics
            "message_length":          message_length,
            "word_count":              word_count,
            "avg_word_length":         round(float(avg_word_length), 3),
            "sentence_count":          sentence_count,
            "caps_ratio":              round(float(caps_ratio), 3),
            "digit_ratio":             round(float(digit_ratio), 3),
            "exclamation_count":       exclamation_count,
            "question_count":          question_count,

            # Entity tokens
            "url_count":               url_count,
            "phone_count":             phone_count,
            "has_otp_token":           has_otp_token,
            "has_amount_token":        has_amount,
            "has_account_token":       has_account,
            "has_upi_token":           has_upi,
            "has_card_token":          has_card,
            "has_ifsc_token":          has_ifsc,

            # Keyword signals
            "has_urgency_keyword":     has_urgency,
            "has_money_keyword":       has_money,
            "has_bank_name":           has_bank_name,
            "has_prize_keyword":       has_prize,
            "has_credential_request":  has_credential,
            "has_upfront_fee":         has_upfront,
            "has_suspicious_domain":   has_suspicious_domain,

            # Composite signals
            "has_otp_request":         has_otp_request,
            "bank_with_suspicious_url":bank_with_suspicious_url,
            "urgency_intensity":       urgency_intensity,

            # Optional indicator columns
            "url_present":             url_present,
            "email_present":           email_present,
            "phone_present":           phone_present,
        }

    @staticmethod
    def _compile_keywords(keywords: List[str]) -> re.Pattern:
        """Compile a list of keywords into a single OR regex pattern."""
        escaped = [re.escape(kw) for kw in sorted(keywords, key=len, reverse=True)]
        pattern = "|".join(escaped)
        return re.compile(pattern, re.IGNORECASE)

    @staticmethod
    def _safe_binary(value, default: bool = False) -> int:
        """Convert optional indicator values to 0/1 with NaN-safe fallback."""
        if value is None:
            return int(default)
        try:
            if pd.isna(value):
                return int(default)
        except TypeError:
            pass
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"", "nan", "none"}:
                return int(default)
            if normalized in {"yes", "true", "y"}:
                return 1
            if normalized in {"no", "false", "n"}:
                return 0
        return int(float(value) > 0)

    # ── Feature Names ─────────────────────────────────────────────────────────
    @property
    def feature_names(self) -> List[str]:
        """Return list of all feature names in extraction order."""
        sample = self._extract_one("sample text url_token", "Sample Text", {})
        return list(sample.keys())

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    # ── Statistics ────────────────────────────────────────────────────────────
    def feature_stats(self, feat_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute summary statistics for all features.
        Useful for EDA in Module 2.
        """
        stats = feat_df.describe().T
        stats["fraud_mean"] = None
        return stats

    def fraud_vs_safe_means(
        self,
        feat_df: pd.DataFrame,
        label_col: pd.Series,
    ) -> pd.DataFrame:
        """
        Compute mean feature values for fraud vs safe records.
        Useful for identifying discriminative features.

        Args:
            feat_df   : features DataFrame
            label_col : Series of "safe" / "fraud" labels

        Returns:
            DataFrame with columns: feature, safe_mean, fraud_mean, difference
        """
        combined = feat_df.copy()
        combined["__label__"] = label_col.values

        rows = []
        for feat in feat_df.columns:
            safe_mean  = combined.loc[combined["__label__"] == "safe",  feat].mean()
            fraud_mean = combined.loc[combined["__label__"] == "fraud", feat].mean()
            rows.append({
                "feature":    feat,
                "safe_mean":  round(float(safe_mean),  4),
                "fraud_mean": round(float(fraud_mean), 4),
                "difference": round(float(fraud_mean - safe_mean), 4),
            })

        return (
            pd.DataFrame(rows)
            .sort_values("difference", ascending=False)
            .reset_index(drop=True)
        )
