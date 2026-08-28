from __future__ import annotations

from fastapi import APIRouter, Query

from app.models import AnalyticsResponse
from app.query_log import get_analytics

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(limit: int = Query(default=10, ge=1, le=50)) -> AnalyticsResponse:
    return get_analytics(limit)
