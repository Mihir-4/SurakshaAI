"""
SurakshaAI — Text Cleaner
==========================
Performs all text preprocessing steps for the financial text pipeline.

Steps applied in order:
  1. Decode HTML entities and strip HTML tags
  2. Normalize Unicode to NFC form
  3. Remove non-printable and control characters
  4. Normalize whitespace
  5. Tokenize financial entities → standard tokens
  6. Lowercase (stored separately; original case preserved)
  7. Remove records too short (< 5 chars) or too long (> 20,000 chars)
  8. Compute SHA-256 checksum for deduplication

Financial entity tokens:
  PHONE_TOKEN    → phone numbers
  URL_TOKEN      → URLs and website links
  ACCOUNT_TOKEN  → bank account numbers
  OTP_TOKEN      → OTP patterns
  AMOUNT_TOKEN   → currency amounts
  UPI_TOKEN      → UPI IDs
  CARD_TOKEN     → card numbers
  IFSC_TOKEN     → IFSC codes

Usage:
    from src.preprocessing.text_cleaner import TextCleaner
    cleaner = TextCleaner()
    result = cleaner.clean("Your SBI OTP is 123456. Click http://sbi.xyz")
    print(result)
    # {
    #   "original_text": "Your SBI OTP is 123456. ...",
    #   "cleaned_text":  "your sbi otp is OTP_TOKEN . click URL_TOKEN",
    #   "checksum":      "abc123...",
    #   "is_valid":      True,
    #   "tokens_found":  {"otp": 1, "url": 1}
    # }
"""

from __future__ import annotations

import hashlib
import html
import logging
import re
import unicodedata
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Financial Entity Regex Patterns ──────────────────────────────────────────
# Order matters: more specific patterns before more general ones

PATTERNS: List[tuple] = [
    # UPI IDs (before phone numbers to avoid partial match)
    (
        "upi",
        re.compile(
            r"\b[a-zA-Z0-9.\-_]{2,256}@"
            r"(okaxis|oksbi|okicici|okhdfcbank|ybl|upi|paytm|"
            r"apl|ibl|axl|icici|sbi|hdfc|kotak|"
            r"allbank|barodampay|centralbank|"
            r"united|utbi|idbi|[a-zA-Z]{2,20})\b",
            re.IGNORECASE,
        ),
        "UPI_TOKEN",
    ),
    # IFSC codes (11 chars: 4 alpha + 0 + 6 alphanumeric)
    (
        "ifsc",
        re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        "IFSC_TOKEN",
    ),
    # Card numbers (16 digits, optionally grouped)
    (
        "card",
        re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        ),
        "CARD_TOKEN",
    ),
    # Account numbers (9–18 digits, standalone)
    (
        "account",
        re.compile(
            r"\b(?:a/?c|account|acc)[\s#:.]*\d{6,18}\b"
            r"|\b\d{9,18}\b",
            re.IGNORECASE,
        ),
        "ACCOUNT_TOKEN",
    ),
    # OTP patterns (4–8 digit codes near "OTP" keyword)
    (
        "otp",
        re.compile(
            r"\b(?:otp|one.?time.?password|verification.?code)"
            r"[\s:is]*\d{4,8}\b"
            r"|\b\d{4,8}\s+(?:is your|as your)\s+(?:otp|code)\b",
            re.IGNORECASE,
        ),
        "OTP_TOKEN",
    ),
    # Currency amounts (Rs., INR, ₹ + number)
    (
        "amount",
        re.compile(
            r"(?:rs\.?|inr|₹)\s*[\d,]+(?:\.\d{1,2})?"
            r"|\b[\d,]+(?:\.\d{1,2})?\s*(?:rs\.?|inr|rupees?|lakhs?|crores?)\b",
            re.IGNORECASE,
        ),
        "AMOUNT_TOKEN",
    ),
    # URLs (http, https, www)
    (
        "url",
        re.compile(
            r"(?:https?://|www\.)[^\s<>\"']{2,}"
            r"|[a-zA-Z0-9\-]+\.[a-zA-Z]{2,6}(?:/[^\s]*)?",
            re.IGNORECASE,
        ),
        "URL_TOKEN",
    ),
    # Phone numbers (Indian: 10 digits starting with 6-9, or with country code)
    (
        "phone",
        re.compile(
            r"(?:\+91[\s\-]?)?[6-9]\d{9}"
            r"|\b(?:1800|1860)\s?\d{3}\s?\d{4}\b"  # toll-free
            r"|\b\d{4}\s?\d{3}\s?\d{3}\b",          # formatted
            re.IGNORECASE,
        ),
        "PHONE_TOKEN",
    ),
]

# ── HTML tag stripper ─────────────────────────────────────────────────────────
_HTML_TAG_RE    = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE    = re.compile(r"\n{2,}")

# ── Control character stripper (keep \n \t) ───────────────────────────────────
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class TextCleaner:
    """
    Cleans and normalizes financial text for the SurakshaAI pipeline.
    Thread-safe: no mutable state after initialization.
    """

    def __init__(
        self,
        min_length: int = 5,
        max_length: int = 20_000,
        lowercase: bool = True,
        tokenize_entities: bool = True,
    ) -> None:
        """
        Args:
            min_length        : discard texts shorter than this (chars)
            max_length        : discard texts longer than this (chars)
            lowercase         : whether to lowercase the cleaned text
            tokenize_entities : whether to replace financial entities with tokens
        """
        self.min_length        = min_length
        self.max_length        = max_length
        self.lowercase         = lowercase
        self.tokenize_entities = tokenize_entities

    # ── Public API ────────────────────────────────────────────────────────────
    def clean(self, text: str) -> dict:
        """
        Clean a single text string.

        Returns:
            dict with keys:
                original_text  : unmodified input
                cleaned_text   : fully processed text
                checksum       : SHA-256 of cleaned lowercased text
                is_valid       : False if text is too short/long/empty
                rejection_reason : reason if is_valid=False, else None
                tokens_found   : dict of entity_type → count
        """
        original = str(text) if text is not None else ""

        result = {
            "original_text":    original,
            "cleaned_text":     "",
            "checksum":         "",
            "is_valid":         False,
            "rejection_reason": None,
            "tokens_found":     {},
        }

        # Empty check
        if not original.strip():
            result["rejection_reason"] = "empty_text"
            return result

        # Pipeline
        cleaned, tokens_found = self._pipeline(original)

        # Length validation
        if len(cleaned) < self.min_length:
            result["rejection_reason"] = (
                f"too_short (len={len(cleaned)}, min={self.min_length})"
            )
            return result

        if len(cleaned) > self.max_length:
            result["rejection_reason"] = (
                f"too_long (len={len(cleaned)}, max={self.max_length})"
            )
            return result

        result["cleaned_text"]  = cleaned
        result["checksum"]      = self._checksum(cleaned.lower())
        result["is_valid"]      = True
        result["tokens_found"]  = tokens_found

        return result

    def clean_series(
        self,
        series,
        show_progress: bool = True,
    ) -> "pd.DataFrame":
        """
        Clean an entire pandas Series of texts.

        Args:
            series       : pd.Series of raw text strings
            show_progress: print progress every 5,000 records

        Returns:
            pd.DataFrame with columns matching the dict from clean()
        """
        import pandas as pd

        results = []
        total   = len(series)

        for i, text in enumerate(series):
            results.append(self.clean(text))
            if show_progress and (i + 1) % 5000 == 0:
                logger.info("Cleaned %d / %d records...", i + 1, total)

        logger.info("Cleaning complete: %d records processed.", total)
        return pd.DataFrame(results)

    def clean_dataframe(
        self,
        df,
        text_col: str,
        drop_invalid: bool = True,
    ):
        """
        Apply cleaning to a DataFrame column.

        Args:
            df           : input DataFrame
            text_col     : column containing raw text
            drop_invalid : if True, remove records that fail validation

        Returns:
            DataFrame with cleaning results merged in.
            Added columns: cleaned_text, checksum, is_valid,
                           rejection_reason, tokens_found
        """
        import pandas as pd

        df = df.copy()
        cleaned_df = self.clean_series(df[text_col])

        df["cleaned_text"]     = cleaned_df["cleaned_text"].values
        df["checksum"]         = cleaned_df["checksum"].values
        df["is_valid"]         = cleaned_df["is_valid"].values
        df["rejection_reason"] = cleaned_df["rejection_reason"].values
        df["tokens_found"]     = cleaned_df["tokens_found"].values

        if drop_invalid:
            before = len(df)
            df = df[df["is_valid"]].copy().reset_index(drop=True)
            after  = len(df)
            logger.info(
                "Dropped %d invalid records (%.1f%%)",
                before - after,
                100 * (before - after) / max(before, 1),
            )

        return df

    # ── Internal Pipeline ─────────────────────────────────────────────────────
    def _pipeline(self, text: str):
        """
        Apply all cleaning steps in sequence.
        Returns (cleaned_text, tokens_found_dict).
        """
        # Step 1: HTML decode and strip
        text = self._strip_html(text)

        # Step 2: Unicode normalization (NFC)
        text = unicodedata.normalize("NFC", text)

        # Step 3: Remove control characters (keep newline and tab)
        text = _CONTROL_RE.sub(" ", text)

        # Step 4: Normalize whitespace
        text = _MULTI_SPACE_RE.sub(" ", text)
        text = _MULTI_NL_RE.sub("\n", text)
        text = text.strip()

        # Step 5: Financial entity tokenization
        tokens_found: Dict[str, int] = {}
        if self.tokenize_entities:
            text, tokens_found = self._tokenize_entities(text)

        # Step 6: Lowercase
        if self.lowercase:
            text = text.lower()

        # Final whitespace cleanup
        text = _MULTI_SPACE_RE.sub(" ", text).strip()

        return text, tokens_found

    @staticmethod
    def _strip_html(text: str) -> str:
        """Decode HTML entities and remove HTML tags."""
        text = html.unescape(text)
        text = _HTML_TAG_RE.sub(" ", text)
        return text

    @staticmethod
    def _tokenize_entities(text: str):
        """
        Replace financial entities with standard tokens.
        Returns (modified_text, tokens_found_dict).
        """
        tokens_found: Dict[str, int] = {}

        for entity_name, pattern, token in PATTERNS:
            matches = pattern.findall(text)
            if matches:
                tokens_found[entity_name] = len(matches)
                text = pattern.sub(f" {token} ", text)

        # Clean up extra spaces introduced by substitution
        text = _MULTI_SPACE_RE.sub(" ", text).strip()

        return text, tokens_found

    @staticmethod
    def _checksum(text: str) -> str:
        """SHA-256 of lowercased cleaned text for deduplication."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ── Deduplication ─────────────────────────────────────────────────────────
    @staticmethod
    def deduplicate(
        df,
        checksum_col: str = "checksum",
        keep: str = "first",
    ):
        """
        Remove duplicate records based on checksum.

        Args:
            df           : DataFrame with checksum column
            checksum_col : name of the checksum column
            keep         : "first" or "last"

        Returns:
            Deduplicated DataFrame.
        """
        before = len(df)
        df_dedup = df.drop_duplicates(subset=[checksum_col], keep=keep)
        after    = len(df_dedup)
        removed  = before - after

        if removed > 0:
            logger.info(
                "Deduplication: removed %d duplicate records (%.1f%%)",
                removed,
                100 * removed / before,
            )

        return df_dedup.reset_index(drop=True)

    # ── Statistics ────────────────────────────────────────────────────────────
    def cleaning_stats(self, df) -> dict:
        """
        Compute statistics about the cleaning process.

        Args:
            df: DataFrame after clean_dataframe() has been applied

        Returns:
            dict of statistics
        """
        total     = len(df)
        valid     = df["is_valid"].sum() if "is_valid" in df.columns else total
        invalid   = total - valid

        reasons   = {}
        if "rejection_reason" in df.columns:
            reasons = (
                df[~df["is_valid"]]["rejection_reason"]
                .value_counts()
                .to_dict()
            )

        return {
            "total_input":       total,
            "valid_output":      int(valid),
            "invalid_dropped":   int(invalid),
            "invalid_pct":       round(100 * invalid / max(total, 1), 2),
            "rejection_reasons": reasons,
        }

    def print_stats(self, df) -> None:
        """Print cleaning statistics to console."""
        stats = self.cleaning_stats(df)
        print("\n  Text Cleaning Statistics")
        print("  " + "─" * 40)
        print(f"  Total input    : {stats['total_input']:>8,}")
        print(f"  Valid output   : {stats['valid_output']:>8,}")
        print(f"  Dropped        : {stats['invalid_dropped']:>8,}  "
              f"({stats['invalid_pct']}%)")
        if stats["rejection_reasons"]:
            print(f"\n  Rejection Reasons:")
            for reason, count in stats["rejection_reasons"].items():
                print(f"    {reason:<35} {count:>6,}")
        print()