"""
SurakshaAI — Centralised Configuration
=======================================
Single source of truth for all application settings.
Uses pydantic-settings to load from environment variables
and .env file automatically.

Usage:
    from src.config import settings
    db_url = settings.DATABASE_URL
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Project root ──────────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str    = "SurakshaAI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool      = True
    LOG_LEVEL: str   = "INFO"

    # ── Database ──────────────────────────────────────────────────────────────
    # Use explicit driver prefix
    DATABASE_URL: str = "postgresql+psycopg2://localhost/surakshaai"

    # ── LLM ───────────────────────────────────────────────────────────────────
    MISTRAL_API_KEY: str          = ""
    MISTRAL_MODEL: str            = "mistral-small-latest"
    MISTRAL_MAX_TOKENS: int       = 1024
    MISTRAL_TEMPERATURE: float    = 0.3
    MISTRAL_RETRY_ATTEMPTS: int   = 3
    MISTRAL_RETRY_DELAY_SECONDS: int = 2

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int          = 10
    ALLOWED_AUDIO_EXTENSIONS: str  = "wav,mp3,m4a,ogg"
    ALLOWED_IMAGE_EXTENSIONS: str  = "png,jpg,jpeg,webp"

    @property
    def allowed_audio_ext(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_AUDIO_EXTENSIONS.split(",")]

    @property
    def allowed_image_ext(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_IMAGE_EXTENSIONS.split(",")]

    # ── Model Paths ───────────────────────────────────────────────────────────
    MODEL_PATH: str           = "./models_store"
    FASTTEXT_MODEL_PATH: str  = "./models_store/nlp/lid.176.bin"

    @property
    def model_dir(self) -> Path:
        return ROOT_DIR / self.MODEL_PATH.lstrip("./")

    @property
    def ml_model_dir(self) -> Path:
        return self.model_dir / "ml"

    @property
    def dl_model_dir(self) -> Path:
        return self.model_dir / "dl"

    @property
    def nlp_model_dir(self) -> Path:
        return self.model_dir / "nlp"

    @property
    def fasttext_path(self) -> Path:
        return ROOT_DIR / self.FASTTEXT_MODEL_PATH.lstrip("./")

    # ── Data Paths ────────────────────────────────────────────────────────────
    @property
    def data_dir(self) -> Path:
        return ROOT_DIR / "data"

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def interim_data_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def processed_data_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def external_data_dir(self) -> Path:
        return self.data_dir / "external"

    @property
    def gold_benchmark_path(self) -> Path:
        return self.external_data_dir / "gold_benchmark.csv"

    @property
    def reports_dir(self) -> Path:
        return ROOT_DIR / "reports"

    # ── Risk Engine Thresholds ────────────────────────────────────────────────
    RISK_LOW_MAX:     float = 0.30
    RISK_CAUTION_MAX: float = 0.55
    RISK_HIGH_MAX:    float = 0.80

    # ── Feature Flags ─────────────────────────────────────────────────────────
    ENABLE_OCR:             bool = True
    ENABLE_SPEECH_TO_TEXT:  bool = True
    ENABLE_QR_DECODE:       bool = True
    ENABLE_LLM_EXPLANATION: bool = True
    ENABLE_TRANSLATION:     bool = True

    # ── ML Training ───────────────────────────────────────────────────────────
    RANDOM_SEED:  int   = 42
    TRAIN_SPLIT:  float = 0.70
    VAL_SPLIT:    float = 0.15
    TEST_SPLIT:   float = 0.15

    # ── Dataset Reliability Weights ───────────────────────────────────────────
    DATASET_WEIGHTS: dict = {
        "financial_scams":    1.0,
        "sms_phishing":       1.0,
        "indian_banking_sms": 0.9,
        "manual_banking":     0.9,
        "manual_loan":        0.9,
        "manual_whatsapp":    0.9,
        "sms_spam":           0.8,
        "phishing_email":     0.7,
        "urls":               1.0,
        "upi":                0.9,
    }

    # ── Financial Keywords ────────────────────────────────────────────────────
    FINANCIAL_KEYWORDS: List[str] = [
        "account", "debit", "credit", "balance", "transaction",
        "bank", "otp", "upi", "imps", "neft", "rtgs", "card",
        "statement", "kyc", "atm", "loan", "emi", "mandate",
        "payment", "withdraw", "deposit", "transfer", "cheque",
        "ifsc", "passbook", "pin", "blocked", "expired", "verify",
    ]

    # ── Supported Languages ───────────────────────────────────────────────────
    SUPPORTED_LANGUAGES: List[str] = [
        "en", "hi", "gu", "mr", "ta", "te", "kn", "bn"
    ]

    LANGUAGE_NAMES: dict = {
        "en": "English",
        "hi": "Hindi",
        "gu": "Gujarati",
        "mr": "Marathi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "bn": "Bengali",
    }

    # ── Channels ──────────────────────────────────────────────────────────────
    VALID_CHANNELS: List[str] = [
        "sms", "whatsapp", "email", "banking_notification",
        "loan_ad", "voice", "url", "qr",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # VALIDATORS
    # ══════════════════════════════════════════════════════════════════════════

    @field_validator("RISK_LOW_MAX", "RISK_CAUTION_MAX", "RISK_HIGH_MAX")
    @classmethod
    def risk_thresholds_in_range(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError(
                f"Risk threshold must be strictly between 0.0 and 1.0, got {v}"
            )
        return v

    @field_validator("TRAIN_SPLIT", "VAL_SPLIT", "TEST_SPLIT")
    @classmethod
    def split_in_range(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError(
                f"Split ratio must be between 0 and 1, got {v}"
            )
        return v

    @model_validator(mode="after")
    def validate_splits_sum_to_one(self) -> "Settings":
        """
        Enforce TRAIN + VAL + TEST == 1.0
        Allows floating-point tolerance of 0.01.
        """
        total = self.TRAIN_SPLIT + self.VAL_SPLIT + self.TEST_SPLIT
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"TRAIN_SPLIT + VAL_SPLIT + TEST_SPLIT must equal 1.0, "
                f"got {self.TRAIN_SPLIT} + {self.VAL_SPLIT} + "
                f"{self.TEST_SPLIT} = {total:.4f}"
            )
        return self

    @model_validator(mode="after")
    def validate_risk_threshold_ordering(self) -> "Settings":
        """
        Enforce RISK_LOW_MAX < RISK_CAUTION_MAX < RISK_HIGH_MAX.
        """
        if not (self.RISK_LOW_MAX < self.RISK_CAUTION_MAX < self.RISK_HIGH_MAX):
            raise ValueError(
                f"Risk thresholds must be strictly increasing: "
                f"RISK_LOW_MAX ({self.RISK_LOW_MAX}) < "
                f"RISK_CAUTION_MAX ({self.RISK_CAUTION_MAX}) < "
                f"RISK_HIGH_MAX ({self.RISK_HIGH_MAX})"
            )
        return self

    # ── Helpers ───────────────────────────────────────────────────────────────
    def ensure_directories(self) -> None:
        """
        Create all required project directories if they do not exist.
        Call this explicitly at application startup — not on import.
        """
        dirs = [
            self.raw_data_dir / "financial_scams",
            self.raw_data_dir / "sms_spam",
            self.raw_data_dir / "sms_phishing",
            self.raw_data_dir / "phishing_email",
            self.raw_data_dir / "indian_banking_sms",
            self.raw_data_dir / "manual_banking",
            self.raw_data_dir / "manual_loan",
            self.raw_data_dir / "manual_whatsapp",
            self.raw_data_dir / "urls",
            self.raw_data_dir / "upi",
            self.interim_data_dir,
            self.processed_data_dir,
            self.external_data_dir,
            self.ml_model_dir,
            self.dl_model_dir / "bilstm",
            self.dl_model_dir / "distilbert",
            self.dl_model_dir / "indicbert",
            self.dl_model_dir / "mbert",
            self.nlp_model_dir,
            self.reports_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Call this everywhere instead of instantiating Settings directly.
    """
    return Settings()


settings: Settings = get_settings()
