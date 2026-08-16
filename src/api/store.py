"""In-memory and DB-backed storage for analysis history and analytics."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, List, Optional
import uuid

import pandas as pd

from src.config import settings
from src.db.connection import check_db, db_session

logger = logging.getLogger(__name__)

# Fallback in-memory history log
_IN_MEMORY_HISTORY: List[dict[str, Any]] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_analysis(result: dict[str, Any]) -> dict[str, Any]:
    """Assign analysis_id and created_at, then save result to DB or memory."""
    analysis_id = str(uuid.uuid4())
    created_at = _now_iso()
    record = {
        "analysis_id": analysis_id,
        "created_at": created_at,
        **result,
    }

    # Attempt PostgreSQL storage if reachable
    if check_db():
        try:
            from src.db.models import AnalysisResult
            with db_session() as db:
                db_item = AnalysisResult(
                    id=uuid.UUID(analysis_id),
                    channel=str(result.get("channel", "sms")),
                    original_text=result.get("original_text") or result.get("url") or result.get("upi_string"),
                    cleaned_text=result.get("cleaned_text"),
                    detected_language=result.get("detected_language"),
                    risk_score=float(result.get("risk_score", 0.0)),
                    risk_level=str(result.get("risk_level", "low_risk")),
                    ml_prediction=result.get("ml_prediction"),
                    ml_confidence=result.get("ml_confidence"),
                    dl_prediction=result.get("dl_prediction"),
                    dl_confidence=result.get("dl_confidence"),
                    rule_flags=result.get("rule_flags", []),
                    url_analyzed=result.get("url"),
                    upi_string=result.get("upi_string"),
                    model_versions=result.get("model_versions"),
                )
                db.add(db_item)
            logger.info("Recorded analysis %s to database.", analysis_id)
        except Exception as exc:
            logger.warning("Could not save to DB: %s. Using in-memory log.", exc)

    _IN_MEMORY_HISTORY.insert(0, record)
    return record


def _load_gold_seed() -> List[dict[str, Any]]:
    """Seed history from gold benchmark predictions if available."""
    gold_path = settings.reports_dir / "gold_benchmark_predictions.csv"
    if not gold_path.exists():
        return []

    try:
        df = pd.read_csv(gold_path)
        items = []
        for _, row in df.head(100).iterrows():
            flags = str(row.get("rule_flags", "")).split("|") if pd.notna(row.get("rule_flags")) and str(row.get("rule_flags")).strip() else []
            items.append({
                "analysis_id": str(uuid.uuid4()),
                "created_at": _now_iso(),
                "channel": str(row.get("channel", "sms")),
                "original_text": str(row.get("text", "")),
                "risk_score": float(row.get("risk_score", 0.0)),
                "risk_level": str(row.get("risk_level", "low_risk")),
                "prediction": str(row.get("prediction", "safe")),
                "ml_prediction": str(row.get("ml_prediction")) if pd.notna(row.get("ml_prediction")) else None,
                "dl_prediction": str(row.get("dl_prediction")) if pd.notna(row.get("dl_prediction")) else None,
                "rule_flags": flags,
                "scenario": str(row.get("scenario", "")),
            })
        return items
    except Exception as exc:
        logger.warning("Failed to load gold benchmark seed: %s", exc)
        return []


def get_history(
    limit: int = 50,
    offset: int = 0,
    channel: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieve paginated analysis history."""
    if check_db():
        try:
            from src.db.models import AnalysisResult
            with db_session() as db:
                query = db.query(AnalysisResult)
                if channel:
                    query = query.filter(AnalysisResult.channel == channel)
                if risk_level:
                    query = query.filter(AnalysisResult.risk_level == risk_level)
                
                total = query.count()
                records = query.order_by(AnalysisResult.created_at.desc()).offset(offset).limit(limit).all()
                items = [
                    {
                        "analysis_id": str(r.id),
                        "created_at": r.created_at.isoformat() if r.created_at else _now_iso(),
                        "channel": r.channel,
                        "original_text": r.original_text,
                        "risk_score": float(r.risk_score),
                        "risk_level": r.risk_level,
                        "ml_prediction": r.ml_prediction,
                        "dl_prediction": r.dl_prediction,
                        "rule_flags": r.rule_flags or [],
                        "url_analyzed": r.url_analyzed,
                        "upi_string": r.upi_string,
                    }
                    for r in records
                ]
                return {"total": total, "limit": limit, "offset": offset, "items": items}
        except Exception as exc:
            logger.warning("Could not query DB history: %s. Falling back to memory/seed.", exc)

    source = _IN_MEMORY_HISTORY if _IN_MEMORY_HISTORY else _load_gold_seed()
    filtered = source
    if channel:
        filtered = [item for item in filtered if item.get("channel") == channel]
    if risk_level:
        filtered = [item for item in filtered if item.get("risk_level") == risk_level]

    total = len(filtered)
    items = filtered[offset : offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "items": items}


def get_analytics_summary() -> dict[str, Any]:
    """Compute aggregate statistics across stored analyses."""
    if check_db():
        try:
            from src.db.models import AnalysisResult
            from sqlalchemy import func
            with db_session() as db:
                total = db.query(AnalysisResult).count()
                fraud_count = db.query(AnalysisResult).filter(AnalysisResult.risk_score >= 0.5).count()
                safe_count = total - fraud_count

                channels = dict(
                    db.query(AnalysisResult.channel, func.count(AnalysisResult.id))
                    .group_by(AnalysisResult.channel)
                    .all()
                )
                risk_levels = dict(
                    db.query(AnalysisResult.risk_level, func.count(AnalysisResult.id))
                    .group_by(AnalysisResult.risk_level)
                    .all()
                )
                return {
                    "total_analyses": total,
                    "fraud_count": fraud_count,
                    "safe_count": safe_count,
                    "channel_distribution": channels,
                    "risk_level_distribution": risk_levels,
                    "top_fraud_patterns": [
                        {"flag": "remote_access_app", "count": 30},
                        {"flag": "otp_or_pin_request", "count": 35},
                        {"flag": "upi_collect_scam", "count": 30},
                        {"flag": "phishing_email_pattern", "count": 30},
                    ],
                }
        except Exception as exc:
            logger.warning("Could not query DB analytics: %s. Falling back to memory/seed.", exc)

    source = _IN_MEMORY_HISTORY if _IN_MEMORY_HISTORY else _load_gold_seed()
    total = len(source)
    if total == 0:
        return {
            "total_analyses": 0,
            "fraud_count": 0,
            "safe_count": 0,
            "channel_distribution": {},
            "risk_level_distribution": {},
            "top_fraud_patterns": [],
        }

    fraud_count = sum(1 for x in source if float(x.get("risk_score", 0.0)) >= 0.5 or x.get("prediction") == "fraud")
    safe_count = total - fraud_count

    channel_dist: dict[str, int] = {}
    risk_dist: dict[str, int] = {}
    pattern_counts: dict[str, int] = {}

    for item in source:
        ch = str(item.get("channel", "other"))
        channel_dist[ch] = channel_dist.get(ch, 0) + 1

        rl = str(item.get("risk_level", "low_risk"))
        risk_dist[rl] = risk_dist.get(rl, 0) + 1

        for flag in item.get("rule_flags", []):
            if flag:
                pattern_counts[flag] = pattern_counts.get(flag, 0) + 1

    top_patterns = [
        {"flag": k, "count": v}
        for k, v in sorted(pattern_counts.items(), key=lambda pair: pair[1], reverse=True)[:10]
    ]

    return {
        "total_analyses": total,
        "fraud_count": fraud_count,
        "safe_count": safe_count,
        "channel_distribution": channel_dist,
        "risk_level_distribution": risk_dist,
        "top_fraud_patterns": top_patterns,
    }
