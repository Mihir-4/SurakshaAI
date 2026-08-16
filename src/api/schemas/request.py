"""API request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    channel: str = "sms"
    language: str = "auto"
    preferred_language: str = "en"  # Language for AI response output


class URLAnalysisRequest(BaseModel):
    url: str = Field(..., min_length=3)


class UPIAnalysisRequest(BaseModel):
    upi_string: str = Field(..., min_length=3)
