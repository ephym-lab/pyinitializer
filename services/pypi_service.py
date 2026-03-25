from __future__ import annotations

import logging
from html.parser import HTMLParser
from typing import List

import httpx

logger = logging.getLogger(__name__)


class SmartParser(HTMLParser):
    def __init__(self, query: str, limit: int):
        super().__init__()
        self.query = query.lower()
        self.limit = limit
        self.prefix_matches: List[str] = []
        self.substring_matches: List[str] = []

    def handle_data(self, data: str):
        name = data.strip().lower()
        if not name:
            return

        total = len(self.prefix_matches) + len(self.substring_matches)
        if total >= self.limit:
            return

        if name.startswith(self.query):
            if name not in self.prefix_matches:
                self.prefix_matches.append(name)

        elif self.query in name:
            if name not in self.substring_matches:
                self.substring_matches.append(name)

    def get_results(self) -> List[str]:
        return (self.prefix_matches + self.substring_matches)[: self.limit]


class PyPIService:
    PYPI_SIMPLE_URL = "https://pypi.org/simple/"
    PYPI_PACKAGE_URL = "https://pypi.org/pypi/{}/json"

    @classmethod
    async def search_packages(cls, query: str, limit: int = 20) -> List[str]:
        if not query.strip():
            return []

        query = query.lower()
        results: List[str] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:

                # ✅ Phase 1: Check exact match
                try:
                    r = await client.get(cls.PYPI_PACKAGE_URL.format(query))
                    if r.status_code == 200:
                        results.append(query)
                except Exception:
                    pass

                # ✅ Phase 2: Streaming search
                parser = SmartParser(query, limit)

                async with client.stream("GET", cls.PYPI_SIMPLE_URL) as response:
                    async for chunk in response.aiter_text():
                        parser.feed(chunk)

                        if len(parser.prefix_matches) >= limit:
                            break

                streamed = parser.get_results()

                # Merge while avoiding duplicates
                for pkg in streamed:
                    if pkg not in results:
                        results.append(pkg)

                return results[:limit]

        except Exception as exc:
            logger.warning("PyPI search failed: %s", exc)
            return []

    @classmethod
    def is_loaded(cls) -> bool:
        return True