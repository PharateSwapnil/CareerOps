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

## 3. Core data model (Milestone 1)

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

A provider-fallback orchestrator (planned, Milestone 3) will try providers in a
configured priority order and fail over automatically on error/timeout.

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
└── providers/
    ├── job_providers/     JobProvider implementations + base.py Protocol
    └── llm_providers/     LLMProvider implementations + base.py Protocol
```

## 6. Frontend layout

Vite + React + TypeScript. No heavy framework opinions yet beyond routing
(`react-router`) — component library / design system decisions are deferred to the
milestone that builds real UI (see `ROADMAP.md`).

## 7. What's built vs. not yet (as of Milestone 2)

Built:
- One real job-provider integration: Greenhouse (`providers/job_providers/greenhouse_provider.py`)
- Synchronous fetch (`POST /jobs/fetch`) and background ingestion (`POST /jobs/ingest`)
  sharing dedupe logic in `services/job_ingestion.py`

Not yet built:
- Additional job-provider integrations (Lever, Ashby, RSS, career-page scraping)
- Actual LLM provider integrations — stubs only
- Semantic search / embeddings
- Browser automation (Playwright)
- Auth beyond a single local user
- Any UI beyond a bare shell

Each of these is a future milestone. See `docs/ROADMAP.md`.

## 8. For a future Claude session

If you're picking this up in a new conversation: read this file and
`docs/ROADMAP.md` first, then run `git log --oneline` to see what's landed. The
standard prompt to resume work is:

> "Analyze the current codebase and implement the next milestone according to the
> architecture document."

Please update this document whenever you make a decision that changes the shape
described here — it's meant to stay accurate, not aspirational.
