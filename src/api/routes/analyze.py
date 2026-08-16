"""Analysis routes."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas.request import TextAnalysisRequest, UPIAnalysisRequest, URLAnalysisRequest
from src.api.store import record_analysis
from src.engine.fraud_engine import FraudDetectionEngine
from src.llm.mistral_client import MistralSafetyClient

router = APIRouter(prefix="/analyze", tags=["analyze"])
engine = FraudDetectionEngine()
llm = MistralSafetyClient()


@router.post("/text")
def analyze_text(payload: TextAnalysisRequest) -> dict:
    result = engine.analyze_text(payload.text, channel=payload.channel, language=payload.language)
    result["llm_response"] = llm.explain(result, language=payload.preferred_language)
    return record_analysis(result)


@router.post("/url")
def analyze_url(payload: URLAnalysisRequest) -> dict:
    result = engine.analyze_url(payload.url)
    result["channel"] = "url"
    return record_analysis(result)


@router.post("/upi")
def analyze_upi(payload: UPIAnalysisRequest) -> dict:
    result = engine.analyze_upi(payload.upi_string)
    result["channel"] = "upi"
    return record_analysis(result)
