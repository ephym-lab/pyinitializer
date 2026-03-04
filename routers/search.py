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
    """
    Search the cached PyPI Simple Index for packages matching the query.

    Returns up to `limit` package names sorted by relevance (prefix matches
    first, then substring matches, then fuzzy matches).

    Note: The index is loaded asynchronously at startup. If it has not yet
    finished loading, an empty list is returned.
    """
    results = pypi_service.search_packages(q, limit=limit)
    return {
        "query": q,
        "results": results,
        "index_loaded": pypi_service.is_loaded(),
    }
