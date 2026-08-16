"""Image upload route — OCR extraction + fraud analysis."""

from __future__ import annotations

import io
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.store import record_analysis
from src.engine.fraud_engine import FraudDetectionEngine
from src.llm.mistral_client import MistralSafetyClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])

_engine: FraudDetectionEngine | None = None
_llm: MistralSafetyClient | None = None


def _get_engine() -> FraudDetectionEngine:
    global _engine
    if _engine is None:
        _engine = FraudDetectionEngine()
    return _engine


def _get_llm() -> MistralSafetyClient:
    global _llm
    if _llm is None:
        _llm = MistralSafetyClient()
    return _llm


def _extract_text_from_image(image_bytes: bytes) -> str:
    """Run OCR on image bytes and return extracted text."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        # Try multilingual OCR: English + Hindi + Marathi/Gujarati (Devanagari)
        text = pytesseract.image_to_string(img, lang="eng+hin")
        return text.strip()
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="OCR not available. Please install: pip install pytesseract Pillow — and install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as exc:
        logger.warning("OCR extraction failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Could not read text from image: {str(exc)}")


@router.post("/image")
async def analyze_image(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
) -> dict:
    """
    Accept an image upload (PNG, JPG, WebP screenshot).
    Extract text via OCR, then run full fraud detection analysis.
    Returns the same schema as /analyze/text with ocr_extracted_text added.
    """
    # Validate file type
    content_type = file.content_type or ""
    if not any(t in content_type for t in ["image/", "application/octet-stream"]):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WebP).")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="Image file too large. Maximum size is 10MB.")

    ocr_text = _extract_text_from_image(image_bytes)
    if not ocr_text or len(ocr_text.strip()) < 5:
        raise HTTPException(
            status_code=422,
            detail="Could not extract readable text from this image. Please try a clearer screenshot."
        )

    engine = _get_engine()
    llm = _get_llm()

    result = engine.analyze_text(ocr_text, channel="image", language=language)
    result["llm_response"] = llm.explain(result, language=language)
    result["ocr_extracted_text"] = ocr_text
    result["source"] = "image_ocr"

    return record_analysis(result)
