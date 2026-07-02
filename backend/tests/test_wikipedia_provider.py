import httpx
import pytest

from app.providers.company_data_providers.wikipedia_provider import WikipediaCompanyProvider


def _mock_transport(status_code: int, payload: dict | None = None) -> httpx.AsyncBaseTransport:
    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if payload is None:
                return httpx.Response(status_code, request=request)
            return httpx.Response(status_code, json=payload, request=request)

    return _Transport()


@pytest.mark.asyncio
async def test_wikipedia_provider_found():
    payload = {
        "type": "standard",
        "extract": "Stripe is a financial services and software company.",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Stripe,_Inc."}},
    }
    client = httpx.AsyncClient(transport=_mock_transport(200, payload))
    provider = WikipediaCompanyProvider(client=client)

    result = await provider.fetch("Stripe")

    assert result.found is True
    assert "financial services" in result.summary_extract
    assert result.source_url == "https://en.wikipedia.org/wiki/Stripe,_Inc."

    await client.aclose()


@pytest.mark.asyncio
async def test_wikipedia_provider_404_returns_not_found():
    client = httpx.AsyncClient(transport=_mock_transport(404))
    provider = WikipediaCompanyProvider(client=client)

    result = await provider.fetch("Some Obscure Startup That Does Not Exist")

    assert result.found is False
    assert result.summary_extract is None

    await client.aclose()


@pytest.mark.asyncio
async def test_wikipedia_provider_disambiguation_returns_not_found():
    payload = {"type": "disambiguation", "extract": "Mercury may refer to..."}
    client = httpx.AsyncClient(transport=_mock_transport(200, payload))
    provider = WikipediaCompanyProvider(client=client)

    result = await provider.fetch("Mercury")

    assert result.found is False

    await client.aclose()
