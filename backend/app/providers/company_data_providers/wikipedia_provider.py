"""CompanyDataProvider backed by Wikipedia's public REST summary API.

Docs: https://en.wikipedia.org/api/rest_v1/ (Wikimedia REST API)
Endpoint: GET https://en.wikipedia.org/api/rest_v1/page/summary/{title}
Public, no auth, but requires a contactable User-Agent header per Wikimedia's
API etiquette policy (enforced in practice, not just documented).

LIMITATION worth being upfront about: this does a direct title lookup on
the company name as given, with no disambiguation/search step. Companies
whose Wikipedia article has a different title (e.g. "Block, Inc." rather
than "Square") or that don't have an article at all will come back as
found=False rather than a wrong/mismatched result - deliberately, since a
best-guess disambiguation could attach the wrong company's facts to a job
posting, which is worse than returning nothing. A real search step against
Wikipedia's search API would improve hit rate; noted in ROADMAP.md as a
natural follow-up rather than built here.
"""
import httpx

from app.providers.company_data_providers.base import CompanyDataProviderError, CompanyDataResult

WIKIPEDIA_SUMMARY_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"
USER_AGENT = "CareerOpsPlusPlus/0.1 (https://github.com/PharateSwapnil/CareerOps; contact via GitHub issues)"


class WikipediaCompanyProvider:
    name = "wikipedia"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch(self, company_name: str) -> CompanyDataResult:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": USER_AGENT}
        )

        try:
            title = company_name.strip().replace(" ", "_")
            resp = await client.get(f"{WIKIPEDIA_SUMMARY_BASE}/{title}")

            if resp.status_code == 404:
                return CompanyDataResult(found=False)

            resp.raise_for_status()
            data = resp.json()

            page_type = data.get("type")
            if page_type in ("disambiguation", "missing", "no-extract"):
                return CompanyDataResult(found=False)

            extract = data.get("extract")
            if not extract:
                return CompanyDataResult(found=False)

            content_urls = data.get("content_urls", {}).get("desktop", {})
            return CompanyDataResult(
                found=True,
                summary_extract=extract,
                source_url=content_urls.get("page"),
            )
        except httpx.HTTPError as exc:
            raise CompanyDataProviderError(f"Wikipedia lookup failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()
