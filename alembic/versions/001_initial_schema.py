"""Initial schema — all SurakshaAI tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00

This migration creates all tables defined in src/db/models.py.
It is the baseline migration for the project.
"""

from __future__ import annotations

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision:  str       = "001"
down_revision          = None
branch_labels          = None
depends_on             = None


def upgrade() -> None:
    # ── dataset_registry ──────────────────────────────────────────────────────
    op.create_table(
        "dataset_registry",
        sa.Column("id",                 sa.Integer(),       primary_key=True, autoincrement=True),
        sa.Column("dataset_name",       sa.String(100),     nullable=False,   unique=True),
        sa.Column("source",             sa.String(50),      nullable=False),
        sa.Column("url",                sa.Text(),          nullable=True),
        sa.Column("local_path",         sa.Text(),          nullable=True),
        sa.Column("format",             sa.String(20),      nullable=True),
        sa.Column("raw_row_count",      sa.Integer(),       server_default="0"),
        sa.Column("valid_row_count",    sa.Integer(),       server_default="0"),
        sa.Column("fraud_count",        sa.Integer(),       server_default="0"),
        sa.Column("safe_count",         sa.Integer(),       server_default="0"),
        sa.Column("unknown_count",      sa.Integer(),       server_default="0"),
        sa.Column("reliability_weight", sa.Numeric(3, 2),   server_default="1.0"),
        sa.Column("channel",            sa.String(50),      nullable=True),
        sa.Column("checksum_sha256",    sa.String(64),      nullable=True),
        sa.Column("status",             sa.String(20),      server_default="pending"),
        sa.Column("notes",              sa.Text(),          nullable=True),
        sa.Column("registered_at",      sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at",         sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── collection_logs ───────────────────────────────────────────────────────
    op.create_table(
        "collection_logs",
        sa.Column("id",            sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("dataset_name",  sa.String(100), sa.ForeignKey("dataset_registry.dataset_name", ondelete="CASCADE"), nullable=False),
        sa.Column("operation",     sa.String(50),  nullable=False),
        sa.Column("status",        sa.String(20),  nullable=False),
        sa.Column("rows_before",   sa.Integer(),   nullable=True),
        sa.Column("rows_after",    sa.Integer(),   nullable=True),
        sa.Column("details",       sa.Text(),      nullable=True),
        sa.Column("error_message", sa.Text(),      nullable=True),
        sa.Column("executed_at",   sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── raw_communications ────────────────────────────────────────────────────
    op.create_table(
        "raw_communications",
        sa.Column("id",                  sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("dataset_name",        sa.String(100),  nullable=False),
        sa.Column("original_text",       sa.Text(),       nullable=False),
        sa.Column("cleaned_text",        sa.Text(),       nullable=True),
        sa.Column("label_original",      sa.String(50),   nullable=True),
        sa.Column("label_standardized",  sa.String(10),   nullable=True),
        sa.Column("channel",             sa.String(50),   nullable=True),
        sa.Column("detected_language",   sa.String(10),   nullable=True),
        sa.Column("lang_confidence",     sa.Numeric(4,3), nullable=True),
        sa.Column("checksum",            sa.String(64),   unique=True, nullable=True),
        sa.Column("is_augmented",        sa.Boolean(),    server_default="false"),
        sa.Column("augmentation_method", sa.String(50),   nullable=True),
        sa.Column("original_id",         sa.BigInteger(), sa.ForeignKey("raw_communications.id"), nullable=True),
        sa.Column("is_manual",           sa.Boolean(),    server_default="false"),
        sa.Column("split_assignment",    sa.String(10),   nullable=True),
        sa.Column("reliability_weight",  sa.Numeric(3,2), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_raw_comm_dataset",   "raw_communications", ["dataset_name"])
    op.create_index("idx_raw_comm_label",     "raw_communications", ["label_standardized"])
    op.create_index("idx_raw_comm_split",     "raw_communications", ["split_assignment"])
    op.create_index("idx_raw_comm_channel",   "raw_communications", ["channel"])
    op.create_index("idx_raw_comm_augmented", "raw_communications", ["is_augmented"])

    # ── raw_urls ──────────────────────────────────────────────────────────────
    op.create_table(
        "raw_urls",
        sa.Column("id",                  sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("dataset_name",        sa.String(100),  nullable=False),
        sa.Column("url",                 sa.Text(),       nullable=False),
        sa.Column("url_type_original",   sa.String(30),   nullable=True),
        sa.Column("label_standardized",  sa.String(10),   nullable=True),
        sa.Column("url_length",          sa.Integer(),    nullable=True),
        sa.Column("domain_length",       sa.Integer(),    nullable=True),
        sa.Column("num_dots",            sa.Integer(),    nullable=True),
        sa.Column("num_hyphens",         sa.Integer(),    nullable=True),
        sa.Column("has_https",           sa.Boolean(),    nullable=True),
        sa.Column("has_ip_address",      sa.Boolean(),    nullable=True),
        sa.Column("domain_entropy",      sa.Numeric(6,4), nullable=True),
        sa.Column("url_entropy",         sa.Numeric(6,4), nullable=True),
        sa.Column("has_shortener",       sa.Boolean(),    nullable=True),
        sa.Column("suspicious_kw_count", sa.Integer(),    nullable=True),
        sa.Column("checksum",            sa.String(64),   unique=True, nullable=True),
        sa.Column("split_assignment",    sa.String(10),   nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_raw_urls_label", "raw_urls", ["label_standardized"])
    op.create_index("idx_raw_urls_split", "raw_urls", ["split_assignment"])

    # ── raw_upi ───────────────────────────────────────────────────────────────
    op.create_table(
        "raw_upi",
        sa.Column("id",                 sa.BigInteger(),  primary_key=True, autoincrement=True),
        sa.Column("dataset_name",       sa.String(100),   nullable=False),
        sa.Column("upi_string",         sa.Text(),        nullable=False),
        sa.Column("vpa",                sa.String(200),   nullable=True),
        sa.Column("payee_name",         sa.String(200),   nullable=True),
        sa.Column("transaction_note",   sa.Text(),        nullable=True),
        sa.Column("amount",             sa.Numeric(12,2), nullable=True),
        sa.Column("currency",           sa.String(10),    server_default="INR"),
        sa.Column("label_standardized", sa.String(10),    nullable=True),
        sa.Column("fraud_pattern",      sa.String(100),   nullable=True),
        sa.Column("vpa_domain",         sa.String(100),   nullable=True),
        sa.Column("split_assignment",   sa.String(10),    nullable=True),
        sa.Column("created_at",         sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_raw_upi_label", "raw_upi", ["label_standardized"])
    op.create_index("idx_raw_upi_split", "raw_upi", ["split_assignment"])

    # ── analysis_results ──────────────────────────────────────────────────────
    op.create_table(
        "analysis_results",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel",            sa.String(50),   nullable=False),
        sa.Column("original_text",      sa.Text(),       nullable=True),
        sa.Column("cleaned_text",       sa.Text(),       nullable=True),
        sa.Column("detected_language",  sa.String(10),   nullable=True),
        sa.Column("translated_text",    sa.Text(),       nullable=True),
        sa.Column("risk_score",         sa.Numeric(5,4), nullable=False),
        sa.Column("risk_level",         sa.String(20),   nullable=False),
        sa.Column("ml_prediction",      sa.String(10),   nullable=True),
        sa.Column("ml_confidence",      sa.Numeric(5,4), nullable=True),
        sa.Column("dl_prediction",      sa.String(10),   nullable=True),
        sa.Column("dl_confidence",      sa.Numeric(5,4), nullable=True),
        sa.Column("rule_flags",         postgresql.JSONB(), server_default="[]"),
        sa.Column("shap_features",      postgresql.JSONB(), server_default="[]"),
        sa.Column("llm_response",       postgresql.JSONB(), nullable=True),
        sa.Column("url_analyzed",       sa.Text(),       nullable=True),
        sa.Column("upi_string",         sa.Text(),       nullable=True),
        sa.Column("audio_transcript",   sa.Text(),       nullable=True),
        sa.Column("ocr_extracted_text", sa.Text(),       nullable=True),
        sa.Column("processing_time_ms", sa.Integer(),    nullable=True),
        sa.Column("model_versions",     postgresql.JSONB(), nullable=True),
        sa.Column("client_ip",          sa.String(45),   nullable=True),
        sa.Column("user_agent",         sa.String(500),  nullable=True),
        sa.Column("created_at",         sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_analysis_channel",    "analysis_results", ["channel"])
    op.create_index("idx_analysis_risk_level", "analysis_results", ["risk_level"])
    op.create_index("idx_analysis_created",    "analysis_results", ["created_at"])

    # ── model_registry ────────────────────────────────────────────────────────
    op.create_table(
        "model_registry",
        sa.Column("id",                  sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column("model_name",          sa.String(100),  nullable=False),
        sa.Column("model_type",          sa.String(30),   nullable=False),
        sa.Column("version",             sa.String(20),   nullable=False),
        sa.Column("file_path",           sa.Text(),       nullable=True),
        sa.Column("accuracy",            sa.Numeric(6,4), nullable=True),
        sa.Column("f1_macro",            sa.Numeric(6,4), nullable=True),
        sa.Column("roc_auc",             sa.Numeric(6,4), nullable=True),
        sa.Column("pr_auc",              sa.Numeric(6,4), nullable=True),
        sa.Column("fraud_recall",        sa.Numeric(6,4), nullable=True),
        sa.Column("false_positive_rate", sa.Numeric(6,4), nullable=True),
        sa.Column("fraud_recall_5fpr",   sa.Numeric(6,4), nullable=True),
        sa.Column("train_samples",       sa.Integer(),    nullable=True),
        sa.Column("val_samples",         sa.Integer(),    nullable=True),
        sa.Column("test_samples",        sa.Integer(),    nullable=True),
        sa.Column("dataset_version",     sa.String(50),   nullable=True),
        sa.Column("feature_version",     sa.String(50),   nullable=True),
        sa.Column("training_seed",       sa.Integer(),    nullable=True),
        sa.Column("calibration_method",  sa.String(30),   nullable=True),
        sa.Column("decision_threshold",  sa.Numeric(5,4), nullable=True),
        sa.Column("git_commit",          sa.String(40),   nullable=True),
        sa.Column("hyperparameters",     postgresql.JSONB(), nullable=True),
        sa.Column("is_production",       sa.Boolean(),    server_default="false"),
        sa.Column("trained_at",          sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("notes",               sa.Text(),       nullable=True),
    )

    # ── fraud_patterns ────────────────────────────────────────────────────────
    op.create_table(
        "fraud_patterns",
        sa.Column("id",           sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column("pattern_name", sa.String(100), nullable=False),
        sa.Column("pattern_type", sa.String(50),  nullable=True),
        sa.Column("count",        sa.Integer(),   server_default="1"),
        sa.Column("last_seen",    sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("example_text", sa.String(200), nullable=True),
        sa.UniqueConstraint("pattern_name", "pattern_type", name="uq_fraud_pattern"),
    )
    op.create_index("idx_fraud_pattern_type",  "fraud_patterns", ["pattern_type"])
    op.create_index("idx_fraud_pattern_count", "fraud_patterns", ["count"])

    # ── pgcrypto for gen_random_uuid() ────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    op.drop_table("fraud_patterns")
    op.drop_table("model_registry")
    op.drop_table("analysis_results")
    op.drop_table("raw_upi")
    op.drop_table("raw_urls")
    op.drop_table("raw_communications")
    op.drop_table("collection_logs")
    op.drop_table("dataset_registry")