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
Wellfound, Remote.co, WorkingNomads, Jobspresso, JustRemote, Pangian,
DynamiteJobs, CitizenRemote, InclusivelyRemote, RemoteNomadJobs,
OpenToWorkRemote, RemoteHealthcareJobs, Jobgether, NoDesk, Workster, Workew,
Remoters, SkipTheDrive, EURemoteJobs, PowerToFly.
Recommend picking 2–3 based on what's actually relevant to the user's job
search rather than building all 20 scrapers up front.

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

## Milestone 3 — LLM provider orchestration
- [ ] Implement `LLMProvider` for Claude (Anthropic API)
- [ ] Implement `LLMProvider` for at least one more (Groq or OpenRouter)
- [ ] Fallback orchestrator with configurable priority + timeout/error handling
- [ ] `/ai/resume-optimize` and `/ai/cover-letter` endpoints

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
