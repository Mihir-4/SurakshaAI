-- ============================================================
-- SurakshaAI — PostgreSQL Schema
-- ============================================================
-- Run this script once to create all tables.
-- The application also creates tables via SQLAlchemy ORM
-- (init_db()), so this file is the human-readable reference.
-- ============================================================

-- Enable uuid generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Dataset Registry ──────────────────────────────────────────────────────────
-- Tracks every raw dataset: source, size, reliability weight, status.
CREATE TABLE IF NOT EXISTS dataset_registry (
    id                  SERIAL PRIMARY KEY,
    dataset_name        VARCHAR(100)    NOT NULL UNIQUE,
    source              VARCHAR(50)     NOT NULL,   -- mendeley | kaggle | manual | synthetic
    url                 TEXT,
    local_path          TEXT,
    format              VARCHAR(20),                -- csv | tsv | xlsx | json
    raw_row_count       INTEGER         DEFAULT 0,
    valid_row_count     INTEGER         DEFAULT 0,
    fraud_count         INTEGER         DEFAULT 0,
    safe_count          INTEGER         DEFAULT 0,
    unknown_count       INTEGER         DEFAULT 0,
    reliability_weight  NUMERIC(3,2)    DEFAULT 1.0,
    channel             VARCHAR(50),                -- sms | email | url | upi | etc.
    checksum_sha256     VARCHAR(64),
    status              VARCHAR(20)     DEFAULT 'pending',
    -- pending | downloaded | validated | cleaned | split | ready
    notes               TEXT,
    registered_at       TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

-- ── Collection Logs ───────────────────────────────────────────────────────────
-- Audit log for every data collection operation.
CREATE TABLE IF NOT EXISTS collection_logs (
    id              SERIAL PRIMARY KEY,
    dataset_name    VARCHAR(100)    NOT NULL,
    operation       VARCHAR(50)     NOT NULL,
    -- download | validate | clean | split | augment | balance
    status          VARCHAR(20)     NOT NULL,
    -- success | failed | skipped
    rows_before     INTEGER,
    rows_after      INTEGER,
    details         TEXT,
    error_message   TEXT,
    executed_at     TIMESTAMPTZ     DEFAULT NOW()
);

-- ── Raw Communications ────────────────────────────────────────────────────────
-- Stores every individual text record from all text datasets.
CREATE TABLE IF NOT EXISTS raw_communications (
    id                  BIGSERIAL PRIMARY KEY,
    dataset_name        VARCHAR(100)    NOT NULL,
    original_text       TEXT            NOT NULL,
    cleaned_text        TEXT,
    label_original      VARCHAR(50),                -- ham | spam | phishing | etc.
    label_standardized  VARCHAR(10),                -- safe | fraud | unknown
    channel             VARCHAR(50),
    detected_language   VARCHAR(10),
    lang_confidence     NUMERIC(4,3),
    checksum            VARCHAR(64)     UNIQUE,     -- SHA-256 of cleaned_text
    is_augmented        BOOLEAN         DEFAULT FALSE,
    augmentation_method VARCHAR(50),
    original_id         BIGINT          REFERENCES raw_communications(id),
    is_manual           BOOLEAN         DEFAULT FALSE,
    split_assignment    VARCHAR(10),                -- train | val | test
    reliability_weight  NUMERIC(3,2),
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_comm_dataset
    ON raw_communications(dataset_name);

CREATE INDEX IF NOT EXISTS idx_raw_comm_label
    ON raw_communications(label_standardized);

CREATE INDEX IF NOT EXISTS idx_raw_comm_split
    ON raw_communications(split_assignment);

CREATE INDEX IF NOT EXISTS idx_raw_comm_channel
    ON raw_communications(channel);

-- ── Raw URLs ──────────────────────────────────────────────────────────────────
-- Stores URL records from the URL phishing dataset.
CREATE TABLE IF NOT EXISTS raw_urls (
    id                  BIGSERIAL PRIMARY KEY,
    dataset_name        VARCHAR(100)    NOT NULL,
    url                 TEXT            NOT NULL,
    url_type_original   VARCHAR(30),                -- benign | phishing | malware | defacement
    label_standardized  VARCHAR(10),                -- safe | fraud
    url_length          INTEGER,
    domain_length       INTEGER,
    num_dots            INTEGER,
    num_hyphens         INTEGER,
    has_https           BOOLEAN,
    has_ip_address      BOOLEAN,
    domain_entropy      NUMERIC(6,4),
    url_entropy         NUMERIC(6,4),
    has_shortener       BOOLEAN,
    suspicious_kw_count INTEGER,
    checksum            VARCHAR(64)     UNIQUE,
    split_assignment    VARCHAR(10),
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_urls_label
    ON raw_urls(label_standardized);

CREATE INDEX IF NOT EXISTS idx_raw_urls_split
    ON raw_urls(split_assignment);

-- ── Raw UPI ───────────────────────────────────────────────────────────────────
-- Stores synthetic UPI payment string records.
CREATE TABLE IF NOT EXISTS raw_upi (
    id                  BIGSERIAL PRIMARY KEY,
    dataset_name        VARCHAR(100)    NOT NULL,
    upi_string          TEXT            NOT NULL,
    vpa                 VARCHAR(200),
    payee_name          VARCHAR(200),
    transaction_note    TEXT,
    amount              NUMERIC(12,2),
    currency            VARCHAR(10)     DEFAULT 'INR',
    label_standardized  VARCHAR(10),                -- safe | fraud
    fraud_pattern       VARCHAR(100),
    vpa_domain          VARCHAR(100),
    split_assignment    VARCHAR(10),
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_upi_label
    ON raw_upi(label_standardized);

-- ── Analysis Results ──────────────────────────────────────────────────────────
-- Stores every analysis performed by the production API.
CREATE TABLE IF NOT EXISTS analysis_results (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(50)     NOT NULL,
    original_text       TEXT,
    cleaned_text        TEXT,
    detected_language   VARCHAR(10),
    translated_text     TEXT,
    risk_score          NUMERIC(4,3)    NOT NULL,
    risk_level          VARCHAR(20)     NOT NULL,
    -- low_risk | caution | high_risk | very_high_risk
    ml_prediction       VARCHAR(10),
    ml_confidence       NUMERIC(4,3),
    dl_prediction       VARCHAR(10),
    dl_confidence       NUMERIC(4,3),
    rule_flags          JSONB           DEFAULT '[]',
    shap_features       JSONB           DEFAULT '[]',
    llm_response        JSONB,
    url_analyzed        TEXT,
    upi_string          TEXT,
    audio_transcript    TEXT,
    ocr_extracted_text  TEXT,
    processing_time_ms  INTEGER,
    model_versions      JSONB,
    client_ip           INET,
    user_agent          TEXT,
    created_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_channel
    ON analysis_results(channel);

CREATE INDEX IF NOT EXISTS idx_analysis_risk_level
    ON analysis_results(risk_level);

CREATE INDEX IF NOT EXISTS idx_analysis_created
    ON analysis_results(created_at DESC);

-- ── Model Registry ────────────────────────────────────────────────────────────
-- Tracks trained model versions and their evaluation metrics.
CREATE TABLE IF NOT EXISTS model_registry (
    id                  SERIAL PRIMARY KEY,
    model_name          VARCHAR(100)    NOT NULL,
    model_type          VARCHAR(30)     NOT NULL,   -- ml | dl | url | upi
    version             VARCHAR(20)     NOT NULL,
    file_path           TEXT,
    accuracy            NUMERIC(6,4),
    f1_macro            NUMERIC(6,4),
    roc_auc             NUMERIC(6,4),
    pr_auc              NUMERIC(6,4),
    fraud_recall        NUMERIC(6,4),
    false_positive_rate NUMERIC(6,4),
    fraud_recall_5fpr   NUMERIC(6,4),
    train_samples       INTEGER,
    val_samples         INTEGER,
    test_samples        INTEGER,
    hyperparameters     JSONB,
    is_production       BOOLEAN         DEFAULT FALSE,
    trained_at          TIMESTAMPTZ     DEFAULT NOW(),
    notes               TEXT
);

-- ── Fraud Patterns ────────────────────────────────────────────────────────────
-- Tracks detected fraud patterns over time for dashboard analytics.
CREATE TABLE IF NOT EXISTS fraud_patterns (
    id              SERIAL PRIMARY KEY,
    pattern_name    VARCHAR(100)    NOT NULL,
    pattern_type    VARCHAR(50),                -- url | content | upi | language
    count           INTEGER         DEFAULT 1,
    last_seen       TIMESTAMPTZ     DEFAULT NOW(),
    example_text    TEXT
);

-- ── Trigger: updated_at on dataset_registry ───────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dataset_registry_updated_at
    ON dataset_registry;

CREATE TRIGGER trg_dataset_registry_updated_at
    BEFORE UPDATE ON dataset_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── Views ─────────────────────────────────────────────────────────────────────

-- Summary view for the analytics dashboard
CREATE OR REPLACE VIEW analytics_summary AS
SELECT
    COUNT(*)                                            AS total_analyses,
    SUM(CASE WHEN risk_level IN ('high_risk','very_high_risk') THEN 1 ELSE 0 END)
                                                        AS high_risk_count,
    SUM(CASE WHEN risk_level = 'very_high_risk' THEN 1 ELSE 0 END)
                                                        AS very_high_risk_count,
    SUM(CASE WHEN risk_level = 'low_risk' THEN 1 ELSE 0 END)
                                                        AS low_risk_count,
    ROUND(AVG(risk_score)::NUMERIC, 3)                  AS avg_risk_score,
    ROUND(AVG(processing_time_ms)::NUMERIC, 1)          AS avg_processing_ms
FROM analysis_results;

-- Channel distribution view
CREATE OR REPLACE VIEW channel_distribution AS
SELECT
    channel,
    COUNT(*)                                            AS total,
    SUM(CASE WHEN risk_level IN ('high_risk','very_high_risk') THEN 1 ELSE 0 END)
                                                        AS fraud_count,
    ROUND(
        100.0 * SUM(CASE WHEN risk_level IN ('high_risk','very_high_risk')
                         THEN 1 ELSE 0 END) / COUNT(*), 1
    )                                                   AS fraud_pct
FROM analysis_results
GROUP BY channel
ORDER BY total DESC;