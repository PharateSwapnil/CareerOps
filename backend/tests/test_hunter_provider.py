import httpx
import pytest

from app.providers.contact_enrichment_providers.hunter_provider import HunterEmailProvider


class _FakeSettings:
    hunter_api_key = "test-hunter-key"


def _mock_transport(status_code: int, payload: dict | None = None) -> httpx.AsyncBaseTransport:
    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if payload is None:
                return httpx.Response(status_code, request=request)
            return httpx.Response(status_code, json=payload, request=request)

    return _Transport()


@pytest.mark.asyncio
async def test_hunter_provider_found(monkeypatch):
    monkeypatch.setattr(
        "app.providers.contact_enrichment_providers.hunter_provider.get_settings",
        lambda: _FakeSettings(),
    )
    payload = {"data": {"email": "alexis@reddit.com", "score": 97}}
    client = httpx.AsyncClient(transport=_mock_transport(200, payload))
    provider = HunterEmailProvider(client=client)

    result = await provider.find_email("Alexis", "Ohanian", "reddit.com")

    assert result.found is True
    assert result.email == "alexis@reddit.com"
    assert result.confidence == 97

    await client.aclose()


@pytest.mark.asyncio
async def test_hunter_provider_no_email_in_response(monkeypatch):
    monkeypatch.setattr(
        "app.providers.contact_enrichment_providers.hunter_provider.get_settings",
        lambda: _FakeSettings(),
    )
    payload = {"data": {"email": None, "score": 0}}
    client = httpx.AsyncClient(transport=_mock_transport(200, payload))
    provider = HunterEmailProvider(client=client)

    result = await provider.find_email("Nobody", "Findable", "example.com")

    assert result.found is False

    await client.aclose()


@pytest.mark.asyncio
async def test_hunter_provider_returns_not_found_without_key():
    """Without HUNTER_API_KEY configured, the provider should return
    found=False rather than erroring - same pattern as Adzuna/Voyage."""
    provider = HunterEmailProvider()
    result = await provider.find_email("Jane", "Doe", "example.com")
    assert result.found is False
