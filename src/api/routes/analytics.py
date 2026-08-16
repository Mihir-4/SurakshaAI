from fastapi import APIRouter

from src.api.store import get_analytics_summary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary() -> dict:
    return get_analytics_summary()
