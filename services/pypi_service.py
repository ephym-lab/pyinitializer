from __future__ import annotations

import logging
from difflib import get_close_matches
from html.parser import HTMLParser
from typing import List

import httpx

logger = logging.getLogger(__name__)

class PyPIParser(HTMLParser):
    """Collects all data from tags (vulnerable to huge pages but fine for simple index)."""

    def __init__(self) -> None:
        super().__init__()
        self.packages: List[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.packages.append(stripped)

class PyPIService:
    """Service for PyPI package index operations."""
    
    PYPI_SIMPLE_URL = "https://pypi.org/simple/"
    _package_index: List[str] = []
    _loaded = False

    @classmethod
    async def load_index(cls) -> None:
        """Fetch and cache the full PyPI simple index. Called at application startup."""
        logger.info("Fetching PyPI simple index from %s …", cls.PYPI_SIMPLE_URL)
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(cls.PYPI_SIMPLE_URL, headers={"Accept": "text/html"})
                response.raise_for_status()

            parser = PyPIParser()
            parser.feed(response.text)
            cls._package_index = [pkg.lower() for pkg in parser.packages if pkg.strip()]
            cls._loaded = True
            logger.info("PyPI index loaded: %d packages cached.", len(cls._package_index))
        except Exception as exc:
            logger.warning(
                "Failed to load PyPI index: %s. Package search will be unavailable.", exc
            )

    @classmethod
    def search_packages(cls, query: str, limit: int = 20) -> List[str]:
        """
        Search cached package names.
        Returns up to `limit` package names sorted by relevance.
        """
        q = query.lower().strip()
        if not q:
            return []

        # 1. Prefix matches
        prefix: List[str] = [p for p in cls._package_index if p.startswith(q)]

        # 2. Substring matches (excluding prefix duplicates)
        prefix_set = set(prefix)
        substring: List[str] = [
            p for p in cls._package_index if q in p and p not in prefix_set
        ]

        results = prefix + substring

        # 3. Fuzzy fallback if we have fewer than `limit` hits
        if len(results) < limit:
            fuzzy = get_close_matches(q, cls._package_index, n=limit, cutoff=0.6)
            seen = set(results)
            for pkg in fuzzy:
                if pkg not in seen:
                    results.append(pkg)
                    seen.add(pkg)

        return results[:limit]

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded
