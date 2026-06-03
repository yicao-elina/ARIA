"""
Literature Searcher -- online search via OpenAlex and Semantic Scholar.

Provides ``search()``, ``search_openalex()``, and
``search_semantic_scholar()`` methods for retrieving and deduplicating
papers relevant to a query.

Ported from ``aria_search_ollama.py`` (lines 36--188).

Author: ARIA Team
"""

import logging
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class LiteratureSearcher:
    """Searches OpenAlex and Semantic Scholar for literature validation.

    Parameters
    ----------
    email : str
        Email for the OpenAlex "polite pool" (faster, higher rate limits).
    """

    def __init__(self, email: str = "research@example.com") -> None:
        self.email = email
        self.openalex_base = "https://api.openalex.org/works"
        self.s2_base = "https://api.semanticscholar.org/graph/v1/paper/search"

        # Rate limiting state
        self._last_request_time: float = 0.0
        self._min_request_interval: float = 0.1  # 100 ms

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 10,
        use_both: bool = True,
    ) -> List[Dict]:
        """Search both APIs and combine results.

        Parameters
        ----------
        query : str
            Free-text search string.
        max_results : int
            Maximum total results to return.
        use_both : bool
            If True, query both OpenAlex and Semantic Scholar.
            If False, only OpenAlex is used.

        Returns
        -------
        list[dict]
            Combined and deduplicated results sorted by citation count.
        """
        results: list[dict] = []

        if use_both:
            openalex_results = self.search_openalex(query, max_results // 2)
            s2_results = self.search_semantic_scholar(query, max_results // 2)
            results = openalex_results + s2_results
        else:
            results = self.search_openalex(query, max_results)

        # Deduplicate by normalised title
        unique_results: list[dict] = []
        seen_titles: set[str] = set()
        for paper in results:
            title_lower = paper["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_results.append(paper)

        # Sort by citations (most cited first)
        unique_results.sort(key=lambda x: x.get("citations", 0), reverse=True)
        return unique_results[:max_results]

    def search_openalex(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search OpenAlex for papers.

        Parameters
        ----------
        query : str
        max_results : int

        Returns
        -------
        list[dict]
            Each dict has keys: ``title``, ``abstract``, ``url``,
            ``year``, ``citations``, ``authors``, ``source``.
        """
        self._rate_limit()

        params = {
            "search": query,
            "per_page": max_results,
            "mailto": self.email,
            "sort": "cited_by_count:desc",
        }

        try:
            response = requests.get(
                self.openalex_base, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            papers: list[dict] = []
            for work in data.get("results", []):
                paper = {
                    "title": work.get("title", "Untitled"),
                    "abstract": work.get("abstract", ""),
                    "url": work.get("id", ""),
                    "year": work.get("publication_year"),
                    "citations": work.get("cited_by_count", 0),
                    "authors": [
                        author.get("author", {}).get("display_name", "Unknown")
                        for author in work.get("authorships", [])[:3]
                    ],
                    "source": "OpenAlex",
                }
                papers.append(paper)
            return papers

        except Exception as exc:
            logger.warning("OpenAlex search failed for '%s': %s", query, exc)
            return []

    def search_semantic_scholar(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict]:
        """Search Semantic Scholar for papers.

        Parameters
        ----------
        query : str
        max_results : int

        Returns
        -------
        list[dict]
            Same structure as ``search_openalex``.
        """
        self._rate_limit()

        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,url,year,citationCount,authors",
        }

        try:
            response = requests.get(
                self.s2_base, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            papers: list[dict] = []
            for paper_data in data.get("data", []):
                paper = {
                    "title": paper_data.get("title", "Untitled"),
                    "abstract": paper_data.get("abstract", ""),
                    "url": paper_data.get("url", ""),
                    "year": paper_data.get("year"),
                    "citations": paper_data.get("citationCount", 0),
                    "authors": [
                        author.get("name", "Unknown")
                        for author in paper_data.get("authors", [])[:3]
                    ],
                    "source": "Semantic Scholar",
                }
                papers.append(paper)
            return papers

        except Exception as exc:
            logger.warning(
                "Semantic Scholar search failed for '%s': %s", query, exc
            )
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Ensure minimum interval between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()