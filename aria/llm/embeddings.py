"""
ARIA Embedding Module.

Provides a unified interface for text embedding generation,
using SentenceTransformer models for local inference.
"""

import logging
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# Default embedding model used across ARIA
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class EmbeddingModel:
    """Lightweight wrapper around SentenceTransformer for embeddings.

    Provides a consistent interface for generating text embeddings
    used in node similarity matching and analogical transfer.

    Parameters
    ----------
    model_name : str
        SentenceTransformer model name. Default is ``"all-MiniLM-L6-v2"``
        which provides good quality at 384 dimensions and ~80MB size.
    cache_folder : str, optional
        Directory to cache downloaded models.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_folder: Optional[str] = None,
    ):
        self.model_name = model_name
        self.cache_folder = cache_folder
        self._model = None

    def _load_model(self):
        """Lazy-load the SentenceTransformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                kwargs = {}
                if self.cache_folder:
                    kwargs["cache_folder"] = self.cache_folder
                self._model = SentenceTransformer(self.model_name, **kwargs)
                logger.info(f"Embedding model loaded: {self.model_name}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                )

    def embed(
        self,
        text: Union[str, List[str]],
        normalize: bool = True,
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """Generate embeddings for text.

        Parameters
        ----------
        text : str or list of str
            Single text string or list of strings to embed.
        normalize : bool
            Whether to L2-normalize the embeddings (default True).

        Returns
        -------
        np.ndarray
            Single embedding vector (if text is str) or
            2D array of embeddings (if text is list of str).
        """
        self._load_model()

        is_single = isinstance(text, str)
        texts = [text] if is_single else text

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )

        return embeddings[0] if is_single else embeddings

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:
        """Compute cosine similarity between two texts.

        Parameters
        ----------
        text_a : str
            First text.
        text_b : str
            Second text.

        Returns
        -------
        float
            Cosine similarity score in [-1, 1].
        """
        emb_a = self.embed(text_a)
        emb_b = self.embed(text_b)
        return float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))

    def batch_similarity(
        self,
        query: str,
        candidates: List[str],
        top_k: Optional[int] = None,
    ) -> List[tuple]:
        """Find the most similar candidates to a query.

        Parameters
        ----------
        query : str
            Query text.
        candidates : list of str
            Candidate texts to compare against.
        top_k : int, optional
            Number of top results to return. If None, return all.

        Returns
        -------
        list of (str, float)
            List of (candidate, similarity_score) tuples, sorted by
            similarity descending.
        """
        query_emb = self.embed(query)
        candidate_embs = self.embed(candidates)

        similarities = np.dot(candidate_embs, query_emb) / (
            np.linalg.norm(candidate_embs, axis=1) * np.linalg.norm(query_emb)
        )

        results = [
            (candidates[i], float(similarities[i]))
            for i in range(len(candidates))
        ]
        results.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            results = results[:top_k]

        return results

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()