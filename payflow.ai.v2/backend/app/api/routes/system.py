"""
System API routes.
"""

from fastapi import APIRouter, Depends
from app.models.response import SystemStatsResponse
from app.services.engine import InsightXEngine
from app.api.deps import get_engine

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    engine: InsightXEngine = Depends(get_engine),
) -> SystemStatsResponse:
    """Get system statistics and health metrics."""
    stats = engine.get_system_stats()
    return SystemStatsResponse(**stats)


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "PayFlow AI"}
