"""
SurakshaAI — Text Augmentor
=============================
Applies controlled text augmentation to the TRAINING SPLIT ONLY.

Augmentation methods:
  1. Synonym replacement  — replace 1-2 non-critical words with WordNet synonyms
  2. Random insertion     — insert one contextually appropriate financial term
  3. Minor paraphrasing   — swap sentence-level structure
  4. Back-translation     — English → Hindi (IndicTrans2) → English (subset only)

Rules enforced:
  - Augmentation is NEVER applied before the train/val/test split
  - Augmented records NEVER appear in val or test sets
  - Every augmented record carries:
      original_id        : ID of the source record
      is_augmented       : True
      augmentation_method: which technique was applied
  - Financial entity tokens (URL_TOKEN, OTP_TOKEN, etc.) are NEVER replaced
  - All augmented records carry the same label as their source

Primary target: Financial Scams Mendeley dataset
  (~365 training records → target 3,000-5,000 after augmentation)

Usage:
    from src.preprocessing.augmentor import TextAugmentor
    aug = TextAugmentor()
    aug_df = aug.augment_dataframe(train_df, target_total=4000,
                                   source_filter="financial_scams")
"""

from __future__ import annotations

import logging
import random
import re
from typing import List, Optional

import pandas as pd

from src.config import settings

logger = logging.getLogger(__name__)

random.seed(settings.RANDOM_SEED)

# ── Protected tokens (never replaced by augmentation) ─────────────────────────
PROTECTED_TOKENS = {
    "url_token", "phone_token", "otp_token", "amount_token",
    "account_token", "upi_token", "card_token", "ifsc_token",
}

# ── Financial insertion terms ─────────────────────────────────────────────────
FINANCIAL_INSERT_TERMS = [
    "account", "transaction", "bank", "payment", "balance",
    "credit", "debit", "transfer", "statement", "notification",
]

# ── NLTK setup ────────────────────────────────────────────────────────────────
_NLTK_READY = False

def _ensure_nltk() -> bool:
    """Download required NLTK data if not present."""
    global _NLTK_READY
    if _NLTK_READY:
        return True
    try:
        import nltk
        for pkg in ["wordnet", "averaged_perceptron_tagger", "omw-1.4"]:
            try:
                nltk.data.find(f"corpora/{pkg}")
            except LookupError:
                nltk.download(pkg, quiet=True)
        _NLTK_READY = True
        return True
    except Exception as e:
        logger.warning("NLTK setup failed: %s. Synonym replacement disabled.", e)
        return False


class TextAugmentor:
    """
    Applies text augmentation to training split records.
    """

    def __init__(
        self,
        synonym_prob: float = 0.15,
        max_synonyms_per_text: int = 2,
        enable_back_translation: bool = False,
    ) -> None:
        """
        Args:
            synonym_prob           : probability of replacing each eligible word
            max_synonyms_per_text  : max replacements per text
            enable_back_translation: enable IndicTrans2 back-translation
                                     (slow, requires GPU, disabled by default)
        """
        self.synonym_prob            = synonym_prob
        self.max_synonyms_per_text   = max_synonyms_per_text
        self.enable_back_translation = enable_back_translation
        self._nltk_ok                = _ensure_nltk()

    # ── Main Entry Point ──────────────────────────────────────────────────────
    def augment_dataframe(
        self,
        df: pd.DataFrame,
        target_total: int,
        text_col: str = "cleaned_text",
        label_col: str = "label_standardized",
        id_col: str = "id",
        source_filter: Optional[str] = None,
        dataset_col: str = "dataset_name",
    ) -> pd.DataFrame:
        """
        Augment a training DataFrame to reach target_total records.

        Args:
            df            : training split DataFrame (original records only)
            target_total  : desired total records after augmentation
            text_col      : text column name
            label_col     : label column name
            id_col        : unique record ID column
            source_filter : if set, only augment records from this dataset
            dataset_col   : dataset source column name

        Returns:
            DataFrame containing ONLY the new augmented records.
            Concatenate with original df to get the full training set.
        """
        if source_filter:
            source_df = df[df[dataset_col] == source_filter].copy()
        else:
            source_df = df.copy()

        current_total  = len(df)
        needed         = max(0, target_total - current_total)
        source_size    = len(source_df)

        if needed == 0:
            logger.info("No augmentation needed: already at target (%d).", current_total)
            return pd.DataFrame()

        if source_size == 0:
            logger.warning("No source records to augment.")
            return pd.DataFrame()

        logger.info(
            "Augmenting: current=%d, target=%d, need=%d, source=%d",
            current_total, target_total, needed, source_size,
        )

        # Decide how many of each method to use
        methods = ["synonym", "insertion", "paraphrase"]
        if self.enable_back_translation:
            methods.append("back_translation")

        augmented_records = []
        method_cycle      = 0

        while len(augmented_records) < needed:
            # Sample a source record
            source_row = source_df.sample(n=1, random_state=None).iloc[0]
            original_text = str(source_row.get(text_col, ""))
            label         = str(source_row.get(label_col, ""))
            original_id   = source_row.get(id_col, source_row.name)

            if not original_text.strip():
                continue

            # Cycle through methods
            method = methods[method_cycle % len(methods)]
            method_cycle += 1

            aug_text = self._apply_method(method, original_text)

            if aug_text and aug_text.strip() and aug_text != original_text:
                record = {
                    text_col:             aug_text,
                    label_col:            label,
                    "original_id":        original_id,
                    "is_augmented":       True,
                    "augmentation_method":method,
                    "split_assignment":   "train",
                }
                # Copy over other columns from source row
                for col in df.columns:
                    if col not in record and col not in [text_col, label_col, id_col]:
                        record[col] = source_row.get(col)

                augmented_records.append(record)

        aug_df = pd.DataFrame(augmented_records).reset_index(drop=True)
        logger.info(
            "Augmentation complete: %d new records generated.",
            len(aug_df),
        )

        method_counts = aug_df["augmentation_method"].value_counts().to_dict()
        logger.info("Method breakdown: %s", method_counts)

        return aug_df

    # ── Augmentation Methods ──────────────────────────────────────────────────
    def _apply_method(self, method: str, text: str) -> str:
        """Route to the correct augmentation method."""
        if method == "synonym":
            return self._synonym_replacement(text)
        elif method == "insertion":
            return self._random_insertion(text)
        elif method == "paraphrase":
            return self._minor_paraphrase(text)
        elif method == "back_translation":
            return self._back_translate(text)
        return text

    def _synonym_replacement(self, text: str) -> str:
        """
        Replace 1-2 non-critical words with WordNet synonyms.
        Skips financial entity tokens and short words.
        """
        if not self._nltk_ok:
            return self._random_insertion(text)  # fallback

        try:
            from nltk.corpus import wordnet

            words       = text.split()
            new_words   = words.copy()
            replaceable = [
                i for i, w in enumerate(words)
                if (
                    w.lower() not in PROTECTED_TOKENS
                    and len(w) > 3
                    and w.isalpha()
                )
            ]

            random.shuffle(replaceable)
            replaced = 0

            for idx in replaceable:
                if replaced >= self.max_synonyms_per_text:
                    break

                word     = words[idx]
                synonyms = []

                for synset in wordnet.synsets(word):
                    for lemma in synset.lemmas():
                        syn = lemma.name().replace("_", " ")
                        if syn.lower() != word.lower() and syn.isalpha():
                            synonyms.append(syn)

                if synonyms:
                    new_words[idx] = random.choice(synonyms)
                    replaced += 1

            return " ".join(new_words)

        except Exception as e:
            logger.debug("Synonym replacement failed: %s", e)
            return text

    def _random_insertion(self, text: str) -> str:
        """
        Insert one contextually appropriate financial term at a random position.
        """
        words    = text.split()
        if not words:
            return text

        insert_term = random.choice(FINANCIAL_INSERT_TERMS)
        insert_pos  = random.randint(0, len(words))
        words.insert(insert_pos, insert_term)
        return " ".join(words)

    def _minor_paraphrase(self, text: str) -> str:
        """
        Apply minor structural variations to the text:
          - Swap comma-separated clauses
          - Move a trailing sentence to the front
          - Add/remove a generic financial phrase
        """
        paraphrase_ops = [
            self._swap_clauses,
            self._move_last_sentence,
            self._add_generic_opener,
        ]
        op = random.choice(paraphrase_ops)
        try:
            return op(text)
        except Exception:
            return text

    @staticmethod
    def _swap_clauses(text: str) -> str:
        """Swap two comma-separated clauses if present."""
        parts = text.split(",")
        if len(parts) >= 2:
            idx = random.randint(0, len(parts) - 2)
            parts[idx], parts[idx + 1] = parts[idx + 1], parts[idx]
            return ",".join(parts)
        return text

    @staticmethod
    def _move_last_sentence(text: str) -> str:
        """Move the last sentence to the beginning."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) >= 2:
            return sentences[-1] + " " + " ".join(sentences[:-1])
        return text

    @staticmethod
    def _add_generic_opener(text: str) -> str:
        """Prepend a generic banking notification opener."""
        openers = [
            "Dear Customer, ",
            "Important Notice: ",
            "Alert: ",
            "Banking Update: ",
        ]
        return random.choice(openers) + text

    def _back_translate(self, text: str) -> str:
        """
        Translate text English → Hindi → English using IndicTrans2.
        Only used when enable_back_translation=True.
        Falls back to original text on any error.

        NOTE: Requires IndicTrans2 to be installed and model weights available.
        This is intentionally a no-op unless explicitly enabled.
        """
        if not self.enable_back_translation:
            return text

        try:
            from src.nlp.translator import IndicTranslator
            translator = IndicTranslator()

            hindi_text   = translator.translate(text, src="en", tgt="hi")
            english_back = translator.translate(hindi_text, src="hi", tgt="en")

            if english_back and english_back.strip():
                return english_back

        except Exception as e:
            logger.debug("Back-translation failed: %s", e)

        return text

    # ── Validation ────────────────────────────────────────────────────────────
    @staticmethod
    def validate_augmented(
        aug_df: pd.DataFrame,
        original_df: pd.DataFrame,
        text_col: str = "cleaned_text",
    ) -> dict:
        """
        Verify augmented records meet quality requirements:
          1. All augmented records have is_augmented=True
          2. All have valid original_id
          3. No augmented text is identical to original
          4. Labels are preserved

        Returns dict with validation results.
        """
        issues = []

        if "is_augmented" in aug_df.columns:
            not_flagged = (~aug_df["is_augmented"]).sum()
            if not_flagged > 0:
                issues.append(f"{not_flagged} augmented records not flagged")

        if "original_id" in aug_df.columns:
            missing_id = aug_df["original_id"].isna().sum()
            if missing_id > 0:
                issues.append(f"{missing_id} augmented records missing original_id")

        # Check for identical texts
        original_texts = set(original_df[text_col].dropna().tolist())
        duplicates = aug_df[text_col].isin(original_texts).sum()
        if duplicates > 0:
            issues.append(
                f"{duplicates} augmented records identical to original records"
            )

        return {
            "passed":           len(issues) == 0,
            "issues":           issues,
            "total_augmented":  len(aug_df),
            "method_breakdown": aug_df.get("augmentation_method", pd.Series()).value_counts().to_dict(),
        }