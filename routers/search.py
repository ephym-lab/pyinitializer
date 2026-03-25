"""
Search router.

GET /search/packages?q=<query> → fuzzy-searches the cached PyPI index.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from services import pypi_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/packages", summary="Search for PyPI packages")
async def search_packages(
    q: str = Query(..., min_length=1, description="Package name search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
):
    results = await pypi_service.PyPIService.search_packages(q, limit=limit)

    return {
        "query": q,
        "results": results,
        "index_loaded": True,
    }
