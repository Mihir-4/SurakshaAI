"""
SurakshaAI — SQLAlchemy ORM Models
=====================================
These models are the single source of truth for the database schema.

schema.sql is a human-readable reference export only.
All schema changes must be made HERE first, then reflected
in an Alembic migration.

Tables:
    DatasetRegistry     — tracks every raw dataset
    CollectionLog       — audit log for pipeline operations
    RawCommunication    — individual text records from all text datasets
    RawURL              — URL records for the URL classifier
    RawUPI              — UPI payment string records
    AnalysisResult      — every production analysis run
    ModelRegistry       — trained model versions and metrics
    FraudPattern        — aggregated fraud pattern tracking

Privacy note:
    AnalysisResult stores original_text and other user content.
    Implement a retention policy before production deployment.
    client_ip is stored only when analytics explicitly require it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.connection import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ══════════════════════════════════════════════════════════════════════════════
# Authentication
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    """
    Application user for personalized history and multilingual preferences.

    Privacy considerations:
      - Password is stored as bcrypt hash — never plaintext
      - preferred_language drives AI response language selection
    """
    __tablename__ = "users"

    id:                 Mapped[uuid.UUID]    = mapped_column(
                                                  UUID(as_uuid=True),
                                                  primary_key=True,
                                                  default=uuid.uuid4,
                                              )
    email:              Mapped[str]          = mapped_column(String(254), nullable=False, unique=True)
    hashed_password:    Mapped[str]          = mapped_column(String(128), nullable=False)
    preferred_language: Mapped[str]          = mapped_column(String(10),  default="en")
    is_active:          Mapped[bool]         = mapped_column(Boolean,     default=True)
    created_at:         Mapped[datetime]     = mapped_column(
                                                  DateTime(timezone=True),
                                                  default=_now,
                                                  server_default=func.now(),
                                              )

    __table_args__ = (
        Index("idx_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} lang={self.preferred_language!r}>"


# ══════════════════════════════════════════════════════════════════════════════
# Dataset Management
# ══════════════════════════════════════════════════════════════════════════════

class DatasetRegistry(Base):
    """
    Tracks every raw dataset used in the project.
    One row per dataset. Updated as the pipeline progresses.
    """
    __tablename__ = "dataset_registry"

    id:                 Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name:       Mapped[str]            = mapped_column(String(100), nullable=False, unique=True)
    source:             Mapped[str]            = mapped_column(String(50),  nullable=False)
    # source options: mendeley | kaggle | manual | synthetic
    url:                Mapped[str | None]     = mapped_column(Text,        nullable=True)
    local_path:         Mapped[str | None]     = mapped_column(Text,        nullable=True)
    format:             Mapped[str | None]     = mapped_column(String(20),  nullable=True)
    raw_row_count:      Mapped[int]            = mapped_column(Integer,     default=0)
    valid_row_count:    Mapped[int]            = mapped_column(Integer,     default=0)
    fraud_count:        Mapped[int]            = mapped_column(Integer,     default=0)
    safe_count:         Mapped[int]            = mapped_column(Integer,     default=0)
    unknown_count:      Mapped[int]            = mapped_column(Integer,     default=0)
    reliability_weight: Mapped[float]          = mapped_column(Numeric(3, 2), default=1.0)
    channel:            Mapped[str | None]     = mapped_column(String(50),  nullable=True)
    checksum_sha256:    Mapped[str | None]     = mapped_column(String(64),  nullable=True)
    status:             Mapped[str]            = mapped_column(
                                                    String(20),
                                                    default="pending",
                                                    nullable=False,
                                                )
    # status options: pending | downloaded | validated | cleaned | split | ready
    notes:              Mapped[str | None]     = mapped_column(Text,        nullable=True)
    registered_at:      Mapped[datetime]       = mapped_column(
                                                    DateTime(timezone=True),
                                                    default=_now,
                                                    server_default=func.now(),
                                                )
    updated_at:         Mapped[datetime]       = mapped_column(
                                                    DateTime(timezone=True),
                                                    default=_now,
                                                    onupdate=_now,
                                                    server_default=func.now(),
                                                )

    # Relationship
    logs: Mapped[list["CollectionLog"]] = relationship(
        "CollectionLog",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<DatasetRegistry {self.dataset_name!r} "
            f"status={self.status!r} rows={self.raw_row_count}>"
        )


class CollectionLog(Base):
    """
    Audit log for every data pipeline operation.
    Append-only: never update, only insert.
    """
    __tablename__ = "collection_logs"

    id:            Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name:  Mapped[str]        = mapped_column(
                                            String(100),
                                            ForeignKey("dataset_registry.dataset_name", ondelete="CASCADE"),
                                            nullable=False,
                                        )
    operation:     Mapped[str]        = mapped_column(String(50),  nullable=False)
    # operation options: download | validate | clean | split | augment | balance
    status:        Mapped[str]        = mapped_column(String(20),  nullable=False)
    # status options: success | failed | skipped
    rows_before:   Mapped[int | None] = mapped_column(Integer,     nullable=True)
    rows_after:    Mapped[int | None] = mapped_column(Integer,     nullable=True)
    details:       Mapped[str | None] = mapped_column(Text,        nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text,        nullable=True)
    executed_at:   Mapped[datetime]   = mapped_column(
                                            DateTime(timezone=True),
                                            default=_now,
                                            server_default=func.now(),
                                        )

    dataset: Mapped["DatasetRegistry"] = relationship(
        "DatasetRegistry",
        back_populates="logs",
    )

    def __repr__(self) -> str:
        return (
            f"<CollectionLog {self.dataset_name!r} "
            f"op={self.operation!r} status={self.status!r}>"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Raw Data
# ══════════════════════════════════════════════════════════════════════════════

class RawCommunication(Base):
    """
    Individual text records from all text-based datasets.
    Covers: SMS, email, WhatsApp, banking notifications, loan ads.
    """
    __tablename__ = "raw_communications"

    id:                  Mapped[int]         = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_name:        Mapped[str]         = mapped_column(String(100), nullable=False)
    original_text:       Mapped[str]         = mapped_column(Text,        nullable=False)
    cleaned_text:        Mapped[str | None]  = mapped_column(Text,        nullable=True)
    label_original:      Mapped[str | None]  = mapped_column(String(50),  nullable=True)
    label_standardized:  Mapped[str | None]  = mapped_column(String(10),  nullable=True)
    # label_standardized: safe | fraud | unknown
    channel:             Mapped[str | None]  = mapped_column(String(50),  nullable=True)
    detected_language:   Mapped[str | None]  = mapped_column(String(10),  nullable=True)
    lang_confidence:     Mapped[float | None]= mapped_column(Numeric(4, 3), nullable=True)
    checksum:            Mapped[str | None]  = mapped_column(String(64),  unique=True, nullable=True)
    is_augmented:        Mapped[bool]        = mapped_column(Boolean,     default=False)
    augmentation_method: Mapped[str | None]  = mapped_column(String(50),  nullable=True)
    original_id:         Mapped[int | None]  = mapped_column(
                                                  BigInteger,
                                                  ForeignKey("raw_communications.id"),
                                                  nullable=True,
                                              )
    is_manual:           Mapped[bool]        = mapped_column(Boolean,     default=False)
    split_assignment:    Mapped[str | None]  = mapped_column(String(10),  nullable=True)
    # split_assignment: train | val | test
    reliability_weight:  Mapped[float | None]= mapped_column(Numeric(3, 2), nullable=True)
    created_at:          Mapped[datetime]    = mapped_column(
                                                  DateTime(timezone=True),
                                                  default=_now,
                                                  server_default=func.now(),
                                              )

    # Self-referential relationship for augmented records
    augmentation_source: Mapped["RawCommunication | None"] = relationship(
        "RawCommunication",
        remote_side="RawCommunication.id",
        foreign_keys=[original_id],
    )

    __table_args__ = (
        Index("idx_raw_comm_dataset",  "dataset_name"),
        Index("idx_raw_comm_label",    "label_standardized"),
        Index("idx_raw_comm_split",    "split_assignment"),
        Index("idx_raw_comm_channel",  "channel"),
        Index("idx_raw_comm_augmented","is_augmented"),
    )

    def __repr__(self) -> str:
        preview = (self.original_text or "")[:40]
        return (
            f"<RawCommunication id={self.id} "
            f"label={self.label_standardized!r} "
            f"text={preview!r}>"
        )


class RawURL(Base):
    """
    URL records for the URL XGBoost classifier.
    Raw text is never fed to a transformer — only extracted features.
    """
    __tablename__ = "raw_urls"

    id:                  Mapped[int]         = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_name:        Mapped[str]         = mapped_column(String(100), nullable=False)
    url:                 Mapped[str]         = mapped_column(Text,        nullable=False)
    url_type_original:   Mapped[str | None]  = mapped_column(String(30),  nullable=True)
    # url_type_original: benign | phishing | malware | defacement
    label_standardized:  Mapped[str | None]  = mapped_column(String(10),  nullable=True)
    # label_standardized: safe | fraud
    url_length:          Mapped[int | None]  = mapped_column(Integer,     nullable=True)
    domain_length:       Mapped[int | None]  = mapped_column(Integer,     nullable=True)
    num_dots:            Mapped[int | None]  = mapped_column(Integer,     nullable=True)
    num_hyphens:         Mapped[int | None]  = mapped_column(Integer,     nullable=True)
    has_https:           Mapped[bool | None] = mapped_column(Boolean,     nullable=True)
    has_ip_address:      Mapped[bool | None] = mapped_column(Boolean,     nullable=True)
    domain_entropy:      Mapped[float | None]= mapped_column(Numeric(6, 4), nullable=True)
    url_entropy:         Mapped[float | None]= mapped_column(Numeric(6, 4), nullable=True)
    has_shortener:       Mapped[bool | None] = mapped_column(Boolean,     nullable=True)
    suspicious_kw_count: Mapped[int | None]  = mapped_column(Integer,     nullable=True)
    checksum:            Mapped[str | None]  = mapped_column(String(64),  unique=True, nullable=True)
    split_assignment:    Mapped[str | None]  = mapped_column(String(10),  nullable=True)
    created_at:          Mapped[datetime]    = mapped_column(
                                                  DateTime(timezone=True),
                                                  default=_now,
                                                  server_default=func.now(),
                                              )

    __table_args__ = (
        Index("idx_raw_urls_label", "label_standardized"),
        Index("idx_raw_urls_split", "split_assignment"),
    )

    def __repr__(self) -> str:
        return f"<RawURL id={self.id} label={self.label_standardized!r} url={self.url[:40]!r}>"


class RawUPI(Base):
    """
    Synthetic UPI payment string records for the UPI XGBoost classifier.
    """
    __tablename__ = "raw_upi"

    id:                 Mapped[int]          = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_name:       Mapped[str]          = mapped_column(String(100),  nullable=False)
    upi_string:         Mapped[str]          = mapped_column(Text,         nullable=False)
    vpa:                Mapped[str | None]   = mapped_column(String(200),  nullable=True)
    payee_name:         Mapped[str | None]   = mapped_column(String(200),  nullable=True)
    transaction_note:   Mapped[str | None]   = mapped_column(Text,         nullable=True)
    amount:             Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency:           Mapped[str]          = mapped_column(String(10),   default="INR")
    label_standardized: Mapped[str | None]   = mapped_column(String(10),   nullable=True)
    fraud_pattern:      Mapped[str | None]   = mapped_column(String(100),  nullable=True)
    vpa_domain:         Mapped[str | None]   = mapped_column(String(100),  nullable=True)
    split_assignment:   Mapped[str | None]   = mapped_column(String(10),   nullable=True)
    created_at:         Mapped[datetime]     = mapped_column(
                                                  DateTime(timezone=True),
                                                  default=_now,
                                                  server_default=func.now(),
                                              )

    __table_args__ = (
        Index("idx_raw_upi_label", "label_standardized"),
        Index("idx_raw_upi_split", "split_assignment"),
    )

    def __repr__(self) -> str:
        return f"<RawUPI id={self.id} vpa={self.vpa!r} label={self.label_standardized!r}>"


# ══════════════════════════════════════════════════════════════════════════════
# Production Analysis
# ══════════════════════════════════════════════════════════════════════════════

class AnalysisResult(Base):
    """
    Every analysis performed by the production API.

    Privacy considerations:
      - original_text may contain sensitive financial information
      - Implement a retention policy (e.g. 90-day TTL) before production
      - client_ip: stored only when required for fraud analytics
      - Consider anonymizing or truncating original_text after N days
    """
    __tablename__ = "analysis_results"

    id:                 Mapped[uuid.UUID]    = mapped_column(
                                                  UUID(as_uuid=True),
                                                  primary_key=True,
                                                  default=uuid.uuid4,
                                              )
    channel:            Mapped[str]          = mapped_column(String(50),   nullable=False)
    original_text:      Mapped[str | None]   = mapped_column(Text,         nullable=True)
    cleaned_text:       Mapped[str | None]   = mapped_column(Text,         nullable=True)
    detected_language:  Mapped[str | None]   = mapped_column(String(10),   nullable=True)
    translated_text:    Mapped[str | None]   = mapped_column(Text,         nullable=True)
    risk_score:         Mapped[float]        = mapped_column(Numeric(5, 4), nullable=False)
    risk_level:         Mapped[str]          = mapped_column(String(20),   nullable=False)
    # risk_level: low_risk | caution | high_risk | very_high_risk
    ml_prediction:      Mapped[str | None]   = mapped_column(String(10),   nullable=True)
    ml_confidence:      Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    dl_prediction:      Mapped[str | None]   = mapped_column(String(10),   nullable=True)
    dl_confidence:      Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    rule_flags:         Mapped[list | None]  = mapped_column(JSONB,         default=list)
    shap_features:      Mapped[list | None]  = mapped_column(JSONB,         default=list)
    llm_response:       Mapped[dict | None]  = mapped_column(JSONB,         nullable=True)
    url_analyzed:       Mapped[str | None]   = mapped_column(Text,          nullable=True)
    upi_string:         Mapped[str | None]   = mapped_column(Text,          nullable=True)
    audio_transcript:   Mapped[str | None]   = mapped_column(Text,          nullable=True)
    ocr_extracted_text: Mapped[str | None]   = mapped_column(Text,          nullable=True)
    processing_time_ms: Mapped[int | None]   = mapped_column(Integer,       nullable=True)
    model_versions:     Mapped[dict | None]  = mapped_column(JSONB,         nullable=True)
    # client_ip: stored only for fraud analytics, not for surveillance
    client_ip:          Mapped[str | None]   = mapped_column(String(45),    nullable=True)
    user_agent:         Mapped[str | None]   = mapped_column(String(500),   nullable=True)
    created_at:         Mapped[datetime]     = mapped_column(
                                                  DateTime(timezone=True),
                                                  default=_now,
                                                  server_default=func.now(),
                                              )

    __table_args__ = (
        Index("idx_analysis_channel",    "channel"),
        Index("idx_analysis_risk_level", "risk_level"),
        Index("idx_analysis_created",    "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisResult id={self.id} "
            f"channel={self.channel!r} "
            f"risk_level={self.risk_level!r} "
            f"score={self.risk_score}>"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Model Registry
# ══════════════════════════════════════════════════════════════════════════════

class ModelRegistryEntry(Base):
    """
    Tracks every trained model version with full reproducibility metadata.

    Reproducibility fields:
        dataset_version   — which version of the processed dataset was used
        feature_version   — which version of the feature engineering was used
        training_seed     — random seed used for training
        calibration_method— how probability calibration was applied
        decision_threshold— classification threshold used in production
        git_commit        — git commit hash at training time (optional)
    """
    __tablename__ = "model_registry"

    id:                  Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name:          Mapped[str]          = mapped_column(String(100),  nullable=False)
    model_type:          Mapped[str]          = mapped_column(String(30),   nullable=False)
    # model_type: ml | dl | url | upi
    version:             Mapped[str]          = mapped_column(String(20),   nullable=False)
    file_path:           Mapped[str | None]   = mapped_column(Text,         nullable=True)

    # Performance metrics
    accuracy:            Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    f1_macro:            Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    roc_auc:             Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    pr_auc:              Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    fraud_recall:        Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    false_positive_rate: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    fraud_recall_5fpr:   Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)

    # Dataset info
    train_samples:       Mapped[int | None]   = mapped_column(Integer,       nullable=True)
    val_samples:         Mapped[int | None]   = mapped_column(Integer,       nullable=True)
    test_samples:        Mapped[int | None]   = mapped_column(Integer,       nullable=True)

    # Reproducibility metadata
    dataset_version:     Mapped[str | None]   = mapped_column(String(50),    nullable=True)
    feature_version:     Mapped[str | None]   = mapped_column(String(50),    nullable=True)
    training_seed:       Mapped[int | None]   = mapped_column(Integer,       nullable=True)
    calibration_method:  Mapped[str | None]   = mapped_column(String(30),    nullable=True)
    # calibration_method: platt_scaling | temperature_scaling | isotonic | none
    decision_threshold:  Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    git_commit:          Mapped[str | None]   = mapped_column(String(40),    nullable=True)

    # Config and state
    hyperparameters:     Mapped[dict | None]  = mapped_column(JSONB,         nullable=True)
    is_production:       Mapped[bool]         = mapped_column(Boolean,       default=False)
    trained_at:          Mapped[datetime]     = mapped_column(
                                                   DateTime(timezone=True),
                                                   default=_now,
                                                   server_default=func.now(),
                                               )
    notes:               Mapped[str | None]   = mapped_column(Text,          nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ModelRegistryEntry {self.model_name!r} "
            f"v{self.version} "
            f"f1={self.f1_macro} "
            f"prod={self.is_production}>"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Analytics
# ══════════════════════════════════════════════════════════════════════════════

class FraudPattern(Base):
    """
    Aggregated fraud pattern tracking for dashboard analytics.

    Design decisions:
      - UNIQUE(pattern_name, pattern_type) prevents duplicate rows
      - Use UPSERT (ON CONFLICT DO UPDATE) to increment count
      - example_text is optional and should not contain user PII
    """
    __tablename__ = "fraud_patterns"

    id:           Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern_name: Mapped[str]        = mapped_column(String(100), nullable=False)
    pattern_type: Mapped[str | None] = mapped_column(String(50),  nullable=True)
    # pattern_type: url | content | upi | language
    count:        Mapped[int]        = mapped_column(Integer,     default=1)
    last_seen:    Mapped[datetime]   = mapped_column(
                                          DateTime(timezone=True),
                                          default=_now,
                                          server_default=func.now(),
                                          onupdate=_now,
                                      )
    # example_text: do NOT store actual user messages here
    # Use only sanitized pattern examples for display purposes
    example_text: Mapped[str | None] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint("pattern_name", "pattern_type", name="uq_fraud_pattern"),
        Index("idx_fraud_pattern_type", "pattern_type"),
        Index("idx_fraud_pattern_count", "count"),
    )

    def __repr__(self) -> str:
        return (
            f"<FraudPattern {self.pattern_name!r} "
            f"type={self.pattern_type!r} "
            f"count={self.count}>"
        )