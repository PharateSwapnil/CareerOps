# CareerOps++ Roadmap

Milestones are designed to be independently shippable. Check items off as they land
and add a dated note + commit hash when a milestone completes.

## Milestone 1 — Scaffold, core data model, local-first storage ✅ (this commit)
- [x] Monorepo structure (backend + frontend)
- [x] FastAPI app skeleton with health check
- [x] SQLModel entities: User, Company, Job, Resume, Application, Contact, Interaction
- [x] SQLite local-first storage wired up
- [x] Job/LLM provider plugin interfaces (Protocol + stub implementations)
- [x] React + Vite + TS frontend shell with routing
- [x] Architecture doc, CI skeleton

## Milestone 2 — Job discovery (single provider) ✅
- [x] Implement a real `JobProvider` for Greenhouse's public job board API
- [x] Job ingestion endpoint + background fetch job (`POST /jobs/ingest`, runs via FastAPI BackgroundTasks)
- [x] Deduplication logic (source_provider + raw_source_id) — extracted into `services/job_ingestion.py`, shared by sync and background paths
- [x] Basic job list UI in frontend (existing Jobs page works unchanged since it's provider-agnostic)

Notes:
- Greenhouse's Job Board API (`boards-api.greenhouse.io`) has no server-side keyword
  search, so keyword/location/remote filtering happens client-side after fetching
  each board's full posting list.
- `JobSearchQuery.board_tokens` lets callers target specific companies' Greenhouse
  boards; defaults to a few public boards (stripe, airbnb, asana) if omitted.
- Verified against the real API shape via web search of Greenhouse's docs and
  covered with mocked-HTTP unit tests (`tests/test_greenhouse_provider.py`);
  live network calls to `boards-api.greenhouse.io` were not reachable from the
  dev sandbox's network allowlist, so a live smoke test should be run in a
  normal environment before relying on it in production.
- Also added **Arbeitnow** and **Remotive** as real providers (both public JSON
  APIs, no key needed) — see `tests/test_public_api_providers.py`.

### Job source backlog (requested, not all built yet)

Sources are grouped by integration difficulty/risk, not by requested order.
Each ✅ below is implemented; everything else is a future PR against the
`JobProvider` interface in `providers/job_providers/base.py`.

**Public APIs / RSS — straightforward `JobProvider` plugins, do these first**
- [x] Greenhouse
- [x] Arbeitnow
- [x] Remotive
- [x] RemoteOK (`remoteok.com/api`)
- [x] Lever (`api.lever.co/v0/postings/{company}`)
- [x] Ashby (`api.ashbyhq.com/posting-api/job-board/{org}`) — field mapping is
      best-effort; not live-verified from this dev sandbox (network egress
      doesn't reach `api.ashbyhq.com`), so smoke-test before relying on it
- [x] Jobicy
- [x] We Work Remotely (RSS feeds per category, parsed with `xml.etree`)
- [x] Adzuna — reference implementation for the "needs a free API key" tier;
      returns `[]` when `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` aren't set rather
      than erroring
- [ ] Himalayas (skipped for now — lower confidence on exact field names
      without a live response to check against; same pattern as Jobicy once
      verified)
- [ ] Workable (ATS, ~same pattern as Lever)
- [ ] Recruitee (ATS, ~same pattern as Lever)
- [ ] Personio (ATS, publishes an XML job feed rather than JSON)
- [ ] USAJobs.gov (needs a free API key + `Authorization-Key` header)
- [ ] Reed.co.uk (needs a free API key, HTTP Basic auth)
- [ ] Jooble (needs a free API key, POST-based)
- [ ] Careerjet (needs a free affiliate key)

Each remaining key-based source follows the same recipe as `AdzunaJobProvider`:
add the key(s) to `core/config.py` + `.env.example`, return `[]` when unset,
implement `_normalize`/`_apply_filters`. Each remaining ATS source follows
the same recipe as `LeverJobProvider`/`GreenhouseJobProvider`: per-company
endpoint via `board_tokens`, client-side filtering.

**HTML scraping — feasible but higher maintenance; do selectively, respect
robots.txt, and expect breakage when a site redesigns**

Of the three requested (Wellfound, Remote.co, NoDesk):
- [x] **Remote.co** — server-rendered, no anti-bot wall, no login wall.
  Scraper anchors on the stable `/job-details/{slug}` URL pattern rather
  than CSS classes, so it's more resilient to styling changes. Written
  against markdown-rendered page content (couldn't reach remote.co directly
  from this dev sandbox's network allowlist to grab raw HTML), so treat the
  DOM-traversal assumptions as needing a live smoke test before trusting
  them in production — see the caveat docstring in
  `providers/job_providers/remoteco_provider.py`.
- [ ] **Wellfound** — deliberately NOT built. It's protected by active
  anti-bot measures (DataDome); third-party scrapers report needing
  residential proxies or stolen session cookies to get even partial
  success. Building a scraper aimed at defeating that protection isn't
  something this project does, regardless of framing — see
  `ARCHITECTURE.md` §1.4 ("assist, don't bypass protections"). If Wellfound
  access matters, the honest path is Milestone 8's user-present browser
  assistance (you're logged in, present, and clicking — the app doesn't
  operate unattended around anti-bot walls).
- [ ] **NoDesk** — deliberately NOT built with a plain scraper. Its job
  listings render client-side via JavaScript after page load; a plain HTTP
  GET returns a shell page with no jobs in it. This needs headless-browser
  infrastructure (Playwright), which is genuinely a Milestone 8 concern
  (browser automation), not a fit for the lightweight `httpx` + BeautifulSoup
  pattern used elsewhere in this tier.

Remaining requested sources (not yet attempted): WorkingNomads, Jobspresso,
JustRemote, Pangian, DynamiteJobs, CitizenRemote, InclusivelyRemote,
RemoteNomadJobs, OpenToWorkRemote, RemoteHealthcareJobs, Jobgether, Workster,
Workew, Remoters, SkipTheDrive, EURemoteJobs, PowerToFly. Recommend
evaluating each the same way as above (server-rendered + no anti-bot vs.
JS-rendered vs. anti-bot-protected) before building, rather than assuming
they're all straightforward.

**Login-gated (LinkedIn, Naukri, Indeed, FlexJobs, VirtualVocations) — NOT
planned as autonomous scraping**
These platforms' Terms of Service generally prohibit automated login and
scraping; doing so risks account suspension/ban and is inconsistent with this
project's "assist, don't bypass protections" principle (see
`ARCHITECTURE.md` §1.4). If/when this is built, it belongs under **Milestone
8 (Browser-Assisted Applications)** as user-present, human-in-the-loop
browser automation — the user stays logged in and present in their own
browser session; CareerOps++ assists rather than operates unattended with
stored credentials.

## Milestone 3 — LLM provider orchestration ✅
- [x] Implement `LLMProvider` for Claude (Anthropic API) — `providers/llm_providers/anthropic_provider.py`
- [x] Implement `LLMProvider` for Groq — `providers/llm_providers/groq_provider.py`
- [x] Fallback orchestrator with configurable priority + timeout/error handling — `services/llm_orchestrator.py`
- [x] `/ai/resume-optimize` and `/ai/cover-letter` endpoints

Notes:
- Default priority is `["claude", "groq", "stub"]` (`Settings.llm_provider_priority`).
  The stub provider is deliberately last in the default chain so `/ai/*`
  endpoints work end-to-end in local dev with zero API keys configured —
  useful for onboarding contributors before they've set anything up.
- Groq's model lineup changed recently: `llama-3.3-70b-versatile` and
  `llama-3.1-8b-instant` were deprecated in June 2026. The Groq provider
  uses `openai/gpt-oss-120b` instead — worth checking Groq's deprecations
  page again if this stops working, since their model rotation is frequent.
- Claude provider uses `claude-sonnet-5` and Anthropic's native Messages API
  shape (`x-api-key` header, `system` as a top-level field rather than a
  role in the messages array — pulled out of `LLMRequest.messages`
  automatically in `AnthropicLLMProvider.complete`).
- Both providers return `[]`/raise `LLMProviderError` (not a crash) when
  their API key isn't configured, so the orchestrator cleanly skips them.
- `/ai/complete` is a low-level passthrough to the orchestrator;
  `/ai/resume-optimize` and `/ai/cover-letter` build tailored prompts on top
  of it (`services/ai_prompts.py`) and are the intended integration points
  for the frontend.
- Frontend: Applications page now has a basic AI Assist panel (paste resume
  + job description, choose resume-optimize or cover-letter, see the
  result and which provider served it) — functional but unstyled; real UI
  polish is Milestone 9.
- Tests: 10 new tests (provider success/missing-key cases, orchestrator
  fallback/timeout/all-fail cases, endpoint-level fallback-to-stub), 31/31
  total passing.

## Milestone 4 — Application management
- [ ] Application CRUD + status state machine
- [ ] Dashboard UI (pipeline view)
- [ ] Resume version history + rollback/diff UI

## Milestone 5 — Semantic job search
- [ ] Embedding generation for jobs + saved searches
- [ ] Vector similarity search (start with sqlite-vss or a simple in-process index)
- [ ] "similar roles" UI

## Milestone 6 — Networking CRM
- [ ] Contact + Interaction CRUD
- [ ] Follow-up reminders
- [ ] AI-generated networking message drafts

## Milestone 7 — Company intelligence
- [ ] Public data aggregation for companies
- [ ] AI-generated company summaries

## Milestone 8 — Browser-assisted applications
- [ ] Playwright integration for autofill on supported ATS platforms
- [ ] Human-in-the-loop pause points (auth, CAPTCHA, ambiguous fields)

## Milestone 9 — Premium UX pass
- [ ] Command palette, keyboard shortcuts, dark/light mode, animations

## Later / ecosystem
- [ ] Plugin marketplace
- [ ] Optional cloud sync
- [ ] Browser extension, mobile companion
