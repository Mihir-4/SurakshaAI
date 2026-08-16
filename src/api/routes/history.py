from typing import Optional
from fastapi import APIRouter, Query

from src.api.store import get_history

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    channel: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> dict:
    return get_history(limit=limit, offset=offset, channel=channel, risk_level=risk_level)
