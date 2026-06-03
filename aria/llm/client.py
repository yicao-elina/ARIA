"""
ARIA LLM client -- unified interface for language model backends.

Provides :class:`OllamaClient` as the default backend, with the same
``generate_json`` / ``generate`` interface that the ARIA reasoners expect.
Ported from ``26KDD/src/ollama_client.py``.

Author: ARIA Team
"""

import json
import logging
import random
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class OllamaClient:
    """Unified client for Ollama LLM interactions.

    Features:
    - Text generation with JSON mode enforcement
    - Automatic retry with exponential backoff
    - Response validation and parsing
    - Embedding generation (delegated to sentence-transformers)

    Parameters
    ----------
    model : str
        Primary model for text generation (e.g. ``"qwen2:7b"``).
    embedding_model : str
        Model for embeddings (default ``"nomic-embed-text"``).
    base_url : str
        Ollama server URL.
    max_retries : int
        Maximum retry attempts on failure.
    timeout : int
        Request timeout in seconds.
    """

    def __init__(
        self,
        model: str = "qwen2:7b",
        embedding_model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.embedding_model = embedding_model
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self._embedding_model_cached = None

        logger.info("OllamaClient initialised: model=%s", model)

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        json_mode: bool = True,
        system_message: Optional[str] = None,
    ) -> str:
        """Generate text with the Ollama model.

        Parameters
        ----------
        prompt : str
        temperature : float
        max_tokens : int
        json_mode : bool
            If True, append a JSON-enforcement instruction.
        system_message : str or None

        Returns
        -------
        str
            Raw model output (JSON string if *json_mode* is True).
        """
        for attempt in range(self.max_retries):
            try:
                cmd = ["ollama", "run", self.model]

                full_prompt = prompt
                if system_message:
                    full_prompt = f"<system>\n{system_message}\n</system>\n{prompt}\n"

                if json_mode:
                    full_prompt += "\n\nIMPORTANT: Respond with ONLY valid JSON. No other text."

                result = subprocess.run(
                    cmd,
                    input=full_prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                if result.returncode == 0:
                    response = result.stdout.strip()
                    if json_mode:
                        try:
                            json.loads(response)
                        except json.JSONDecodeError:
                            extracted = self._extract_json(response)
                            if extracted:
                                response = extracted
                            else:
                                raise ValueError("Failed to extract valid JSON from response")
                    logger.debug("Generated response (%d chars)", len(response))
                    return response

                raise RuntimeError(f"Ollama error: {result.stderr}")

            except subprocess.TimeoutExpired:
                logger.warning("Timeout on attempt %d/%d", attempt + 1, self.max_retries)
                if attempt < self.max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info("Retrying in %.1fs...", delay)
                    time.sleep(delay)
                else:
                    raise TimeoutError(
                        f"Generation timed out after {self.max_retries} attempts"
                    )

            except Exception as exc:
                logger.warning("Error on attempt %d/%d: %s", attempt + 1, self.max_retries, exc)
                if attempt < self.max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
                else:
                    raise RuntimeError(f"Generation failed: {exc}") from exc

        raise RuntimeError("Unreachable")  # pragma: no cover

    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate and parse a JSON response.

        Parameters
        ----------
        prompt : str
        temperature : float
        max_tokens : int
        system_message : str or None

        Returns
        -------
        dict
            Parsed JSON response.
        """
        response = self.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            system_message=system_message,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse JSON response: {exc}\nResponse: {response}"
            ) from exc

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Try multiple strategies to extract JSON from text."""
        # Strategy 1: JSON code block
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            try:
                json.loads(match.group(1))
                return match.group(1)
            except json.JSONDecodeError:
                pass

        # Strategy 2: Plain code block
        match = re.search(r"```\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            try:
                json.loads(match.group(1))
                return match.group(1)
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find JSON object
        match = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
        if match:
            try:
                json.loads(match.group(0))
                return match.group(0)
            except json.JSONDecodeError:
                pass

        return None

    # ------------------------------------------------------------------
    # Embeddings (delegated to sentence-transformers)
    # ------------------------------------------------------------------

    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using sentence-transformers.

        Parameters
        ----------
        text : str or list[str]

        Returns
        -------
        list[float] or list[list[float]]
        """
        try:
            from sentence_transformers import SentenceTransformer

            if self._embedding_model_cached is None:
                logger.info("Loading embedding model: %s", self.embedding_model)
                self._embedding_model_cached = SentenceTransformer("all-MiniLM-L6-v2")

            is_single = isinstance(text, str)
            texts = [text] if is_single else text
            embeddings = self._embedding_model_cached.encode(texts, convert_to_numpy=True)
            result = embeddings.tolist()
            return result[0] if is_single else result

        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

    # ------------------------------------------------------------------
    # Batch & diagnostics
    # ------------------------------------------------------------------

    def batch_generate(
        self,
        prompts: List[str],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        json_mode: bool = True,
    ) -> List[str]:
        """Generate responses for multiple prompts sequentially."""
        responses = []
        for i, prompt in enumerate(prompts):
            logger.info("Processing prompt %d/%d", i + 1, len(prompts))
            response = self.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
            responses.append(response)
        return responses

    def test_connection(self) -> bool:
        """Test if the client can communicate with Ollama."""
        try:
            response = self.generate(
                prompt='Hello, this is a test. Respond with: {"status": "ok"}',
                json_mode=True,
                max_tokens=50,
            )
            data = json.loads(response)
            return data.get("status") == "ok"
        except Exception as exc:
            logger.error("Connection test failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def get_client(
    model: str = "qwen2:7b",
    backend: str = "ollama",
    base_url: str = "http://localhost:11434",
    **kwargs,
) -> OllamaClient:
    """Factory function to create an LLM client.

    Parameters
    ----------
    model : str
        Model name (e.g., "qwen2:7b", "gpt-4o").
    backend : str
        Backend type: "ollama" (default) or "openai".
    base_url : str
        API base URL.
    **kwargs
        Additional keyword arguments passed to the client constructor.

    Returns
    -------
    OllamaClient
        An LLM client instance.
    """
    if backend == "ollama":
        return OllamaClient(model=model, base_url=base_url, **kwargs)
    elif backend == "openai":
        try:
            from aria.llm.openai_client import OpenAIClient
            return OpenAIClient(model=model, **kwargs)
        except ImportError:
            raise ImportError(
                "OpenAI backend requires the 'openai' package. "
                "Install with: pip install aria-materials[openai]"
            )
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'ollama' or 'openai'.")