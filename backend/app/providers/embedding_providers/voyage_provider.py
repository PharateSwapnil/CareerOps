"""EmbeddingProvider for Voyage AI's text embeddings API.

Docs: https://docs.voyageai.com/docs/embeddings
Endpoint: POST https://api.voyageai.com/v1/embeddings

Unlike the hashing fallback, this produces real neural embeddings capable of
cross-terminology semantic matching (e.g. a "Snowflake/Databricks/PySpark"
query surfacing an "Analytics Engineer" posting even without literal keyword
overlap) - this is the provider to configure for the semantic search quality
described in the original project spec.

Uses voyage-4-lite by default (Voyage's recommendation for lowest latency
and cost while still being part of their current-generation model family).
Reads VOYAGE_API_KEY from Settings; raises EmbeddingProviderError if it's
missing or the request fails.
"""
import httpx

from app.core.config import get_settings
from app.providers.embedding_providers.base import EmbeddingProviderError

VOYAGE_EMBEDDINGS_URL = "https://api.voyageai.com/v1/embeddings"
DEFAULT_MODEL = "voyage-4-lite"
DEFAULT_DIMENSION = 1024


class VoyageEmbeddingProvider:
    name = "voyage"
    model = DEFAULT_MODEL
    dimension = DEFAULT_DIMENSION

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def embed(self, texts: list[str], input_type: str = "document") -> list[list[float]]:
        settings = get_settings()
        if not settings.voyage_api_key:
            raise EmbeddingProviderError("VOYAGE_API_KEY is not configured")

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)

        try:
            resp = await client.post(
                VOYAGE_EMBEDDINGS_URL,
                json={
                    "input": texts,
                    "model": self.model,
                    "input_type": input_type,
                },
                headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            # Voyage returns results with an `index` field but not
            # necessarily in input order in all cases - sort defensively.
            ordered = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
            return [item["embedding"] for item in ordered]
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(f"Voyage embedding request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()
