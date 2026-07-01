import math

import pytest

from app.providers.embedding_providers.hashing_provider import HashingEmbeddingProvider


@pytest.mark.asyncio
async def test_hashing_provider_returns_correct_dimension():
    provider = HashingEmbeddingProvider()
    vectors = await provider.embed(["senior backend engineer python"])
    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimension


@pytest.mark.asyncio
async def test_hashing_provider_is_deterministic():
    provider = HashingEmbeddingProvider()
    v1 = (await provider.embed(["data engineer with spark and airflow"]))[0]
    v2 = (await provider.embed(["data engineer with spark and airflow"]))[0]
    assert v1 == v2


@pytest.mark.asyncio
async def test_hashing_provider_vectors_are_normalized():
    provider = HashingEmbeddingProvider()
    vectors = await provider.embed(["a fairly long job description about python and cloud infra"])
    norm = math.sqrt(sum(v * v for v in vectors[0]))
    assert abs(norm - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_hashing_provider_empty_text_returns_zero_vector():
    provider = HashingEmbeddingProvider()
    vectors = await provider.embed([""])
    assert all(v == 0.0 for v in vectors[0])


@pytest.mark.asyncio
async def test_similar_texts_score_higher_than_dissimilar():
    """Sanity check that shared vocabulary increases cosine similarity -
    this is lexical overlap, not true semantic understanding (see the
    provider's module docstring), but it should still behave predictably."""
    from app.services.embeddings import cosine_similarity

    provider = HashingEmbeddingProvider()
    query = (await provider.embed(["python backend engineer"]))[0]
    close = (await provider.embed(["senior python backend engineer role"]))[0]
    far = (await provider.embed(["marketing coordinator social media"]))[0]

    assert cosine_similarity(query, close) > cosine_similarity(query, far)
