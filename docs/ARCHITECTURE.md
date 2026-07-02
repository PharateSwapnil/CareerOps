# CareerOps++ Architecture

This document is the source of truth for how CareerOps++ is structured. Future
implementation work (by Claude or any contributor) should read this before adding
features, and update it when architecture decisions change.

## 1. Guiding principles

1. **Local-first** — SQLite is the default datastore. No feature should *require* a
   cloud account to function.
2. **Plugin-based** — job sources and LLM providers are adapters behind a common
   interface (`JobProvider`, `LLMProvider`). Adding a new source/model should not
   require touching core business logic.
3. **Normalize everything** — regardless of where a job posting or AI provider
   response comes from, it is converted into a common internal schema before the
   rest of the app touches it.
4. **Assist, don't deceive** — browser automation fills forms and pauses for the
   human on auth/CAPTCHA/ambiguous fields. It never tries to defeat anti-bot
   protections.
5. **Incremental delivery** — the system is built and shipped in milestones (see
   `ROADMAP.md`), each of which is independently useful and testable.

## 2. High-level system diagram

```
                         ┌─────────────────────────┐
                         │        Frontend          │
                         │   React + TS (Vite)      │
                         └────────────┬─────────────┘
                                      │ REST (JSON)
                         ┌────────────▼─────────────┐
                         │      FastAPI Backend      │
                         │  ┌──────────────────────┐ │
                         │  │   API routes layer    │ │
                         │  └──────────┬───────────┘ │
                         │  ┌──────────▼───────────┐ │
                         │  │   Service layer        │ │
                         │  └──────────┬───────────┘ │
        ┌────────────────┼─────────────┼──────────────┼───────────────┐
        │                │             │              │               │
┌───────▼──────┐ ┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ Job Providers │ │ LLM Providers │ │ Storage  │ │ Browser      │ │ Semantic     │
│ (plugins)     │ │ (plugins)     │ │ (SQLite) │ │ Automation   │ │ Search       │
│ Greenhouse    │ │ Groq          │ │          │ │ (Playwright) │ │ (embeddings) │
│ Lever         │ │ Claude        │ │          │ │              │ │              │
│ Ashby         │ │ OpenRouter    │ │          │ │              │ │              │
│ RSS           │ │ Gemini        │ │          │ │              │ │              │
└───────────────┘ └───────────────┘ └──────────┘ └──────────────┘ └──────────────┘
```

## 3. Core data model

Entities live in `backend/app/models/`. All use SQLModel (SQLAlchemy + Pydantic).

| Entity        | Purpose                                                             |
|---------------|----------------------------------------------------------------------|
| `User`        | Local user profile: skills, goals, preferences                     |
| `Company`     | Normalized company record + AI-generated intelligence summary       |
| `Job`         | Normalized job posting, regardless of source provider               |
| `Resume`      | Versioned resume — every generated/edited version is kept           |
| `Application` | Links `User` + `Job` + `Resume` version + lifecycle status/history  |
| `Contact`     | Networking CRM entry (recruiter, hiring manager, referral, etc.)    |
| `Interaction` | A logged touch-point with a `Contact` (message, call, follow-up)    |
| `JobEmbedding`| One embedding vector per (Job, provider) - see Milestone 5           |
| `SavedSearch` | A persisted semantic query + its own embedding, for repeat matching |

Design notes:
- `Job.raw_source_id` + `Job.source_provider` together are unique — this is how we
  dedupe postings scraped from multiple providers.
- `Resume` versions are immutable once created; edits create a new version row with
  `parent_version_id` set, enabling rollback/diff.
- `Application.status` is an enum-backed state machine (see `models/application.py`)
  so the dashboard can render a consistent pipeline view.

## 4. Plugin interfaces

### 4.1 Job providers

Every job source implements `JobProvider` (`backend/app/providers/job_providers/base.py`):

```python
class JobProvider(Protocol):
    name: str  # unique provider id, e.g. "greenhouse"

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        """Fetch and normalize postings from this source."""
```

`NormalizedJob` is the common schema every provider must map its raw response into
(see `schemas/job.py`). This keeps the rest of the app provider-agnostic.

### 4.2 LLM providers

Every model backend implements `LLMProvider` (`backend/app/providers/llm_providers/base.py`):

```python
class LLMProvider(Protocol):
    name: str  # e.g. "claude", "groq", "openrouter", "gemini"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Run a completion; raise LLMProviderError on failure so the
        orchestrator can fall back to the next provider."""
```

A provider-fallback orchestrator (`services/llm_orchestrator.py`, built in
Milestone 3) tries providers in a configured priority order
(`Settings.llm_provider_priority`, default `["claude", "groq", "stub"]`) and
fails over automatically on error/timeout, raising `AllProvidersFailedError`
only if every provider in the chain fails.

### 4.3 Embedding providers

Every embedding backend implements `EmbeddingProvider`
(`backend/app/providers/embedding_providers/base.py`):

```python
class EmbeddingProvider(Protocol):
    name: str
    model: str
    dimension: int

    async def embed(self, texts: list[str], input_type: str = "document") -> list[list[float]]:
        """Embed a batch of texts."""
```

`Settings.embedding_default_provider` (default `"hashing"`, a local
zero-dependency fallback) picks which provider `services/embeddings.py` uses
for auto-embedding on job ingestion and for search when the caller doesn't
specify one. `"voyage"` is available when `VOYAGE_API_KEY` is configured, for
real neural embeddings.

### 4.4 Company data providers

Every public company-data source implements `CompanyDataProvider`
(`backend/app/providers/company_data_providers/base.py`):

```python
class CompanyDataProvider(Protocol):
    name: str

    async def fetch(self, company_name: str) -> CompanyDataResult:
        """Look up public data; returns found=False (not an exception)
        when nothing matches."""
```

Only `"wikipedia"` is implemented (Milestone 7). A provider failure
degrades to `found=False` rather than breaking enrichment - see
`services/company_intelligence.py`.

## 5. Backend layout

```
backend/app/
├── main.py            FastAPI app factory, router registration
├── core/
│   ├── config.py       Settings (env-driven, pydantic-settings)
│   └── security.py     (future) auth/session handling
├── db/
│   └── session.py       engine + session factory, SQLite by default
├── models/               SQLModel entities (one file per entity)
├── schemas/              Pydantic I/O schemas, decoupled from ORM models
├── api/routes/            one router module per resource
├── services/              business logic shared across routes (state
│                          machines, orchestrators, versioning, enrichment)
└── providers/
    ├── job_providers/           JobProvider implementations + base.py Protocol
    ├── llm_providers/           LLMProvider implementations + base.py Protocol
    ├── embedding_providers/     EmbeddingProvider implementations + base.py Protocol
    └── company_data_providers/  CompanyDataProvider implementations + base.py Protocol
```

## 6. Frontend layout

Vite + React + TypeScript. Routing via `react-router`. A real design token
system (`src/index.css`, dark/light via `data-theme` + CSS custom
properties) and a functional command palette (`src/components/CommandPalette.tsx`,
⌘K) landed in Milestone 9. Each page's own internal layout is still fairly
plain inline-flexbox - functional across every shipped milestone (Dashboard,
Jobs, Saved Searches, Companies, Applications, Resumes, Network, Profile),
but not yet a full per-page interaction redesign (drag-and-drop kanban,
animated transitions, etc.) - see `ROADMAP.md` Milestone 9 notes for
exactly what was and wasn't done in that pass.

## 7. What's built vs. not yet (as of Milestone 9)

All 9 core milestones from the original roadmap are now built (see
`docs/ROADMAP.md` for full details and honesty notes on each). Summary:

Built:
- Ten real job-provider integrations: Greenhouse, Arbeitnow, Remotive,
  RemoteOK, Lever, Ashby, Jobicy, We Work Remotely (RSS), Adzuna, and
  Remote.co (HTML scrape) — see `providers/job_providers/` and
  `docs/ROADMAP.md` for per-provider notes and confidence caveats (Ashby's
  and Remote.co's field/DOM mappings aren't live-verified from this dev
  sandbox's restricted network)
- Synchronous fetch (`POST /jobs/fetch`) and background ingestion (`POST /jobs/ingest`)
  sharing dedupe logic in `services/job_ingestion.py`, which also auto-links
  each job to a `Company` record and auto-embeds it for semantic search
- Two real LLM-provider integrations (Claude via Anthropic's Messages API,
  Groq via its OpenAI-compatible endpoint) behind a fallback orchestrator
  (`services/llm_orchestrator.py`) that tries providers in priority order
  and degrades to a stub provider if nothing is configured
- `/ai/resume-optimize`, `/ai/cover-letter`, and `/ai/networking-message`
  endpoints with dedicated prompt-construction logic (`services/ai_prompts.py`)
- Application CRUD with an explicit status state machine
  (`services/application_state_machine.py`) enforced server-side
- Resume version-chain management (`services/resume_versioning.py`):
  immutable versions, chain history lookup, unified diff between versions,
  and rollback-by-creating-a-new-head-version
- A single-local-user shim (`services/default_user.py`) that Applications,
  Resumes, and Contacts attach to until real auth exists
- Semantic job search: pluggable embedding providers (local hashing-trick
  default + optional Voyage AI neural embeddings), in-process cosine
  similarity search (`services/embeddings.py`), auto-embedding on job
  ingestion, "similar roles" lookup, and saved searches with persisted
  query embeddings for repeat matching
- Networking CRM: Contact + Interaction CRUD, a follow-ups-due query, and
  AI-drafted networking messages the user reviews and edits before sending
- Company intelligence: jobs auto-link to `Company` records on ingestion;
  tech stack inferred locally from a company's own ingested job postings;
  pluggable `CompanyDataProvider` (Wikipedia) for external public data;
  AI-generated culture/reputation summaries grounded in those signals, with
  `salary_insights` deliberately left ungenerated rather than hallucinated
- Browser-assisted applications: pure, fully-tested field-classification
  logic (`services/browser_automation/field_classifier.py`) decides what
  to autofill and when to pause, kept separate from the actual Playwright-
  driving code (`playwright_driver.py`, not live-tested in this sandbox -
  see ROADMAP.md). Hard safety rules: headed-only, never solves CAPTCHAs,
  never authenticates, never clicks Submit - the human always does that
  final step themselves. `ApplicationAutomationSession` is a durable audit
  log; the live browser handle is process-local.
- A real design token system (dark/light, `frontend/src/index.css`), a
  functional command palette (⌘K), single-key navigation shortcuts, and
  restrained/reduced-motion-respecting animation - see ROADMAP.md
  Milestone 9 for the specific palette/type choices and what's still
  deferred (full per-page interaction redesign)
- A real (if plainly styled) frontend across all of the above: Dashboard
  pipeline view, Jobs (fetch/semantic search/similar roles), Saved
  Searches, Companies, Applications (+ AI assist), Resumes (versioning UI),
  Network (CRM + follow-ups + AI drafting)

Not yet built / known gaps (all honestly tracked, not swept under anything):
- Real auth / multi-user support (still the single-local-user shim from
  Milestone 4)
- A resume-to-PDF/DOCX export pipeline - without it, Milestone 8's
  autofill uploads a `.txt` file to resume-upload fields, which many real
  ATS forms will reject
- `playwright_driver.py` (Milestone 8) has never been run against a real
  browser or a real application form - this dev sandbox can't download the
  Chromium binary. Verify manually before relying on it.
- Most of the job-source backlog cataloged in `docs/ROADMAP.md` (Himalayas,
  Workable, Recruitee, Personio, Reed, Jooble, Careerjet, USAJobs, and most
  of the requested HTML-scraping tier)
- A real salary/compensation data source (`Company.salary_insights` stays
  null rather than AI-hallucinated)
- Full per-page UI/interaction redesign (Milestone 9 built the shared
  design system - tokens, command palette, theme switching - but each
  page's own layout is still fairly plain inline-flexbox, not the
  Linear/Raycast-level polish - drag-and-drop kanban, animated
  transitions per-page - the original spec envisions)
- Test database isolation (tests still share a persistent SQLite file
  rather than an isolated per-run DB - flagged since Milestone 4)
- Everything in the original spec's "Later / ecosystem" tier: plugin
  marketplace, optional cloud sync, browser extension, mobile companion,
  team/recruiter collaboration

Each of these is tracked in `docs/ROADMAP.md`.

## 8. For a future Claude session

If you're picking this up in a new conversation: read this file and
`docs/ROADMAP.md` first, then run `git log --oneline` to see what's landed.

All 9 core milestones are now complete. There is no more "next milestone"
for the old resume prompt to point to - work from here should be scoped to
one of the tracked gaps instead (see section 7 above and the "Known gap" /
"Not yet built" notes throughout `ROADMAP.md`), roughly in priority order
for actually using this tool day-to-day:

1. A resume-to-PDF/DOCX export pipeline - Milestone 8's autofill is
   structurally complete but not genuinely useful until resumes can be
   uploaded as real documents, not `.txt` files.
2. Manually verify `playwright_driver.py` against a real browser and a
   real Greenhouse/Lever application form - it was never executable in the
   dev sandbox it was written in.
3. Real auth / multi-user support, replacing the single-local-user shim.
4. Whichever job sources from the `docs/ROADMAP.md` backlog are actually
   relevant to the person's own job search - don't build the whole list
   speculatively.
5. Per-page interaction polish (Milestone 9 built the shared design system;
   individual pages could still use real layout work).

A reasonable resume prompt now: "Read ARCHITECTURE.md and ROADMAP.md, then
work on [specific gap from the list above]." Pick one at a time rather than
attempting several in one session - that's been the pattern that's kept
each milestone reviewable.

Please update this document whenever you make a decision that changes the shape
described here — it's meant to stay accurate, not aspirational.
