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

Vite + React + TypeScript. Routing via `react-router`; pages are functional
across all shipped milestones (Dashboard, Jobs, Saved Searches, Companies,
Applications, Resumes, Network) but styled with plain inline CSS rather
than a real design system - the "Linear/Raycast/Vercel/Notion-inspired"
visual polish described in the original spec is explicitly deferred to
Milestone 9 (see `ROADMAP.md`), not attempted piecemeal per-milestone.

## 7. What's built vs. not yet (as of Milestone 7)

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
- A real (if plainly styled) frontend across all of the above: Dashboard
  pipeline view, Jobs (fetch/semantic search/similar roles), Saved
  Searches, Companies, Applications (+ AI assist), Resumes (versioning UI),
  Network (CRM + follow-ups + AI drafting)

Not yet built:
- Browser-assisted applications (Playwright-based autofill) - Milestone 8
- Premium UX pass (command palette, keyboard shortcuts, dark/light mode,
  real design system) - Milestone 9; current UI is functional, plainly
  styled inline CSS, not the "Linear/Raycast/Vercel/Notion-inspired"
  polish described in the original spec
- Real auth / multi-user support (still the single-local-user shim)
- Most of the job-source backlog cataloged in `docs/ROADMAP.md` (Himalayas,
  Workable, Recruitee, Personio, Reed, Jooble, Careerjet, USAJobs, and most
  of the requested HTML-scraping tier)
- A real salary/compensation data source (so `Company.salary_insights` can
  finally be populated with real numbers instead of staying null)
- Test database isolation (tests still share a persistent SQLite file
  rather than an isolated per-run DB - flagged since Milestone 4, not yet
  fixed)

Each of these is tracked in `docs/ROADMAP.md`.

## 8. For a future Claude session

If you're picking this up in a new conversation: read this file and
`docs/ROADMAP.md` first, then run `git log --oneline` to see what's landed. The
standard prompt to resume work is:

> "Analyze the current codebase and implement the next milestone according to the
> architecture document."

Please update this document whenever you make a decision that changes the shape
described here — it's meant to stay accurate, not aspirational.
