"""
Node similarity matching for analogical (Tier-2) retrieval.

Ported from ``_precompute_node_embeddings`` and ``_find_most_similar_node``
in ``aria_core_ollama.py``.  The :class:`NodeMatcher` pre-computes
embeddings for all KG nodes so that similarity queries are fast at
inference time.

Typical usage::

    from aria.kg.graph_store import load_kg
    from aria.retrieval.similarity import NodeMatcher

    graph = load_kg("kg.json")
    matcher = NodeMatcher(graph, model_name="all-MiniLM-L6-v2")
    matcher.precompute()

    hits = matcher.find_similar("CVD temperature 750C", top_k=5)
    for node, score in hits:
        print(f"{node}: {score:.3f}")
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity as _cosine_similarity
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False

import networkx as nx

logger = logging.getLogger(__name__)


class NodeMatcher:
    """Embedding-based similarity search over KG node labels.

    Parameters
    ----------
    graph:
        Directed NetworkX graph whose node labels will be embedded.
    model_name:
        Sentence-Transformer model name.  Defaults to
        ``"all-MiniLM-L6-v2"``.
    """

    def __init__(
        self,
        graph: nx.DiGraph,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        if not _HAS_DEPS:
            raise ImportError(
                "NodeMatcher requires sentence-transformers and scikit-learn.  "
                "Install with: pip install sentence-transformers scikit-learn"
            )

        self.graph = graph
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
        self._node_list: List[str] = []
        self._node_embeddings: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the SentenceTransformer model."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    # ------------------------------------------------------------------
    # Precompute
    # ------------------------------------------------------------------

    def precompute(self) -> None:
        """Pre-compute embeddings for all KG nodes.

        Call this once after initialisation (or after the graph changes)
        before calling :meth:`find_similar`.  If the graph has no nodes,
        a warning is logged and the embeddings array is left empty.
        """
        self._node_list = list(self.graph.nodes())

        if not self._node_list:
            logger.warning("No nodes in KG -- embeddings will be empty")
            self._node_embeddings = np.array([])
            return

        logger.info("Pre-computing embeddings for %d nodes …", len(self._node_list))
        self._node_embeddings = self.model.encode(self._node_list, convert_to_tensor=False)
        logger.info("Embeddings computed for %d nodes", len(self._node_list))

    # ------------------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------------------

    def find_similar(
        self,
        query: str,
        candidates: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Find the most similar nodes to *query* by cosine similarity.

        Parameters
        ----------
        query:
            Query string (e.g. ``"CVD temperature 750C"``).
        candidates:
            Optional list of node labels to restrict the search to.
            If *None*, all nodes in the graph are considered.
        top_k:
            Maximum number of results to return.

        Returns
        -------
        list of (node_label, similarity_score)
            Sorted in descending order of similarity.  If no candidates
            match or no embeddings are available, an empty list is
            returned.
        """
        if self._node_embeddings is None or self._node_embeddings.size == 0:
            logger.warning("Embeddings not computed -- call precompute() first")
            return []

        # Encode query
        query_embedding = self.model.encode([query])

        # Determine candidate indices
        if candidates is not None:
            candidate_indices = [
                i for i, node in enumerate(self._node_list)
                if node in candidates
            ]
        else:
            candidate_indices = list(range(len(self._node_list)))

        if not candidate_indices:
            return []

        # Gather embeddings for candidates
        candidate_embeddings = self._node_embeddings[candidate_indices]

        # Compute similarities
        similarities = _cosine_similarity(query_embedding, candidate_embeddings)[0]

        # Sort by similarity descending
        scored = [
            (self._node_list[idx], float(similarities[j]))
            for j, idx in enumerate(candidate_indices)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:top_k]

    # ------------------------------------------------------------------
    # Convenience: single best match
    # ------------------------------------------------------------------

    def find_most_similar(
        self,
        query: str,
        candidates: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], float]:
        """Return the single most similar node and its score.

        Parameters
        ----------
        query:
            Query string.
        candidates:
            Optional list of candidate node labels.

        Returns
        -------
        (node_label, similarity) or (None, 0.0)
            Best match.  Returns ``(None, 0.0)`` if no candidates are
            available or embeddings have not been computed.
        """
        results = self.find_similar(query, candidates, top_k=1)
        if not results:
            return None, 0.0
        return results[0]

    # ------------------------------------------------------------------
    # Distance helper
    # ------------------------------------------------------------------

    def embedding_distance(self, text_a: str, text_b: str) -> float:
        """Cosine *distance* (1 - cosine_similarity) between two texts.

        Returns
        -------
        float
            Distance in [0, 2].  0 means identical, 1 means orthogonal,
            2 means opposite.
        """
        if not text_a or not text_b:
            return 1.0

        embeddings = self.model.encode([text_a, text_b])
        similarity = _cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(1.0 - similarity)