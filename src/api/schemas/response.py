"""API response schemas."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    analysis_id: Optional[UUID] = None
    channel: Optional[str] = None
    original_text: Optional[str] = None
    risk_score: float
    risk_level: str
    ml_prediction: Optional[str] = None
    ml_confidence: Optional[float] = None
    dl_prediction: Optional[str] = None
    dl_confidence: Optional[float] = None
    rule_flags: list[str] = []
    shap_features: list[dict[str, Any]] = []
    llm_response: Optional[dict[str, Any]] = None
