"""
PyPI package index service.

Fetches the full PyPI Simple Index on startup, caches all package names in
memory, and provides a fast fuzzy-search function for autocomplete.
"""
from __future__ import annotations

import logging
import re
from difflib import get_close_matches
from html.parser import HTMLParser
from typing import List

import httpx

logger = logging.getLogger(__name__)

# Module-level cache

_package_index: List[str] = []

PYPI_SIMPLE_URL = "https://pypi.org/simple/"
_INDEX_LOADED = False


# HTML parser

class _AnchorParser(HTMLParser):
    """Collects all href values from <a> tags."""

    def __init__(self) -> None:
        super().__init__()
        self.packages: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    # The href on PyPI simple index is like /simple/package-name/
                    # Extract the package name from the link text instead; we
                    # handle that in handle_data.
                    pass

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.packages.append(stripped)


# Public API

async def load_index() -> None:
    """Fetch and cache the full PyPI simple index. Called at application startup."""
    global _package_index, _INDEX_LOADED

    logger.info("Fetching PyPI simple index from %s …", PYPI_SIMPLE_URL)
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(PYPI_SIMPLE_URL, headers={"Accept": "text/html"})
            response.raise_for_status()

        parser = _AnchorParser()
        parser.feed(response.text)
        _package_index = [pkg.lower() for pkg in parser.packages if pkg.strip()]
        _INDEX_LOADED = True
        logger.info("PyPI index loaded: %d packages cached.", len(_package_index))
    except Exception as exc:
        logger.warning(
            "Failed to load PyPI index: %s. Package search will be unavailable.", exc
        )


def search_packages(query: str, limit: int = 20) -> List[str]:
    """
    Search cached package names.

    Strategy:
    1. Exact prefix match (highest priority)
    2. Substring match
    3. difflib close-matches as fallback

    Returns up to `limit` results.
    """
    q = query.lower().strip()
    if not q:
        return []

    # 1. Prefix matches
    prefix: List[str] = [p for p in _package_index if p.startswith(q)]

    # 2. Substring matches (excluding prefix duplicates)
    prefix_set = set(prefix)
    substring: List[str] = [
        p for p in _package_index if q in p and p not in prefix_set
    ]

    results = prefix + substring

    # 3. Fuzzy fallback if we have fewer than `limit` hits
    if len(results) < limit:
        fuzzy = get_close_matches(q, _package_index, n=limit, cutoff=0.6)
        seen = set(results)
        for pkg in fuzzy:
            if pkg not in seen:
                results.append(pkg)
                seen.add(pkg)

    return results[:limit]


def is_loaded() -> bool:
    return _INDEX_LOADED
