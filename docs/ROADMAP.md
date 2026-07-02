# CareerOps++ Roadmap

Milestones are designed to be independently shippable. Check items off as they land
and add a dated note + commit hash when a milestone completes.

## Milestone 1 — Scaffold, core data model, local-first storage ✅
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

## Milestone 4 — Application management ✅
- [x] Application CRUD + status state machine
- [x] Dashboard UI (pipeline view)
- [x] Resume version history + rollback/diff UI

Notes:
- State machine lives in `services/application_state_machine.py` as an
  explicit `ALLOWED_TRANSITIONS` map (SAVED → APPLIED → PHONE_SCREEN →
  INTERVIEWING → OFFER, with REJECTED/WITHDRAWN reachable from any active
  stage and terminal once reached). `PATCH /applications/{id}/status`
  enforces it server-side (409 on an illegal transition); the dashboard UI
  only ever offers legal next-steps as buttons, but the backend is the
  source of truth either way.
- No real auth yet (still out of scope per `ARCHITECTURE.md`), so
  `services/default_user.py` get-or-creates a single local user record that
  Applications/Resumes attach to. This is explicitly flagged as a temporary
  shim to replace once auth exists, not a design decision to build on.
- Resume versioning (`services/resume_versioning.py`) keeps every version
  row immutable; edits and rollbacks both create a *new* row extending the
  chain (rollback = "create a new head version with old content", it never
  rewrites history). Chain membership is discovered by walking
  `parent_version_id` pointers rather than assuming a fixed shape, so it
  stays correct after a rollback creates a new branch tip. Diffing uses
  Python's stdlib `difflib.unified_diff`.
- `GET /resumes` returns only the latest version per chain (so the list
  view isn't cluttered with every historical draft); `GET
  /resumes/{id}/history` returns the full chain for a given resume.
- Found and fixed a latent bug while adding these tests: the stub job
  provider hardcoded `raw_source_id="stub-1"` regardless of search keyword,
  so two different test-time searches would collide via the
  source_provider+raw_source_id dedupe key and silently return stale data.
  Fixed to vary the id by keyword.
- Frontend: Dashboard is now a real (if plainly styled) kanban-style
  pipeline view reading live application/job data, with per-card
  "move to next stage" / "reject" buttons wired to the state-machine
  endpoint. Jobs page got an "Add to pipeline" button. Resumes page
  supports creating resumes, viewing version history, diffing adjacent
  versions, adding new versions, and rolling back. The AI Assist panel
  (Milestone 3) can now save its resume-optimize output directly as a new
  Resume.
- Tests: 24 new tests (state machine transition rules, resume versioning
  service logic, full API flows for both Applications and Resumes),
  51/51 total passing.

Known gap carried forward: tests share a persistent SQLite file
(`backend/data/careerops.db`) rather than an isolated per-run database, so
cross-test-file pollution is possible (as the stub-provider bug above
demonstrated). Worth introducing a proper test-fixture override of
`DATABASE_URL` to an in-memory or temp-file DB in a future cleanup pass.

## Milestone 5 — Semantic job search ✅
- [x] Embedding generation for jobs + saved searches
- [x] Vector similarity search (in-process cosine similarity, per the
      roadmap's own "start simple" guidance - see notes)
- [x] "similar roles" UI

Notes:
- Two embedding providers, same plugin pattern as job/LLM providers
  (`providers/embedding_providers/`):
  - **`hashing`** (default, zero setup): a local feature-hashing /
    "hashing trick" bag-of-words vectorizer, no API key, no network call,
    fully deterministic. Captures lexical/n-gram overlap, not true neural
    semantics - it won't reliably connect e.g. a "Snowflake, Databricks,
    PySpark" query to an "Analytics Engineer" posting unless that
    vocabulary literally co-occurs somewhere in the text. This is called
    out explicitly in the provider's own docstring rather than oversold as
    full semantic search.
  - **`voyage`** (opt-in via `VOYAGE_API_KEY`): real neural embeddings via
    Voyage AI's API (`voyage-4-lite` by default), capable of the
    cross-terminology matching the original project spec describes. Built
    against Voyage's documented request/response shape (confirmed via their
    docs), but **not live-verified** - `api.voyageai.com` isn't in this dev
    sandbox's network egress allowlist, so unlike the Claude/Groq providers
    in Milestone 3 I couldn't confirm reachability with even an auth-error
    response. Worth a real smoke test with a configured key before relying
    on it.
- Storage: `JobEmbedding` (one row per job+provider, upserted on re-embed)
  and embedding fields directly on `SavedSearch` (a saved search only needs
  one embedding of its own query text). Vectors are stored as JSON-encoded
  float lists - simple, and fine at this scale.
- Search: deliberately NOT using sqlite-vss or a vector DB.
  `services/embeddings.py` loads all stored vectors for a provider into
  memory and does a linear cosine-similarity scan. At personal-job-search
  scale (hundreds to low thousands of postings) this is fast and avoids the
  real fragility of loadable SQLite extensions across platforms/Python
  builds. If the corpus ever grows enough for this to matter, swapping in a
  real vector index only touches this one module.
- Jobs are auto-embedded (with the default provider) right after ingestion
  in `services/job_ingestion.py`, so semantic search works immediately with
  no separate manual step. A failure to embed doesn't fail the ingestion
  itself - logged and swallowed.
- New endpoints: `POST /jobs/semantic-search`, `GET /jobs/{id}/similar`,
  and full Saved Search CRUD (`POST/GET/DELETE /saved-searches`,
  `GET /saved-searches/{id}/matches`).
- Frontend: Jobs page has a semantic search box and a "Similar roles"
  button per listing; new Saved Searches page for creating/viewing/deleting
  saved semantic searches and their current matches.
- Tests: 15 new tests (hashing provider determinism/normalization/ranking
  behavior, embeddings service upsert/search/similarity logic, full API
  flows for semantic search + similar jobs + saved searches), 66/66 total
  passing. Frontend typechecks clean.

## Milestone 6 — Networking CRM ✅
- [x] Contact + Interaction CRUD
- [x] Follow-up reminders
- [x] AI-generated networking message drafts

Notes:
- Contact and Interaction models already existed from Milestone 1's
  scaffold; this milestone added the CRUD routes, follow-ups query, and AI
  drafting on top of them.
- `GET /contacts/follow-ups?days_ahead=N` returns contacts with a
  `next_follow_up_at` at or before `now + N days`, overdue-first then
  soonest-upcoming (a single sort, since overdue timestamps sort earliest
  naturally). Contacts with no follow-up set are excluded, not treated as
  "always due."
- Interactions are nested under their contact
  (`/contacts/{id}/interactions`) rather than being a top-level resource,
  since they only ever make sense in that context - matches the "logged
  touch-point with a Contact" framing from the original data model.
- `POST /ai/networking-message` follows the same pattern as
  resume-optimize/cover-letter from Milestone 3 (LLM orchestrator +
  dedicated prompt builder in `services/ai_prompts.py`), parameterized by
  contact name/relationship, purpose, optional context, tone, and channel
  (LinkedIn vs. email length/formality). The system prompt explicitly frames
  drafts as a starting point for the user to edit, not a final message -
  keeping the user in control per the original project spec's "AI should
  generate personalized networking messages while keeping the user in
  control" requirement.
- Frontend: Network page has an add-contact form, a follow-ups-due view
  (default) vs. all-contacts view, a per-contact detail panel for setting
  the next follow-up date, logging interactions, viewing interaction
  history, and generating an AI message draft inline.
- Tests: 8 new tests (contact/interaction CRUD, missing-contact 404s,
  follow-up windowing and sort order, networking-message endpoint),
  74/74 total passing. Frontend typechecks clean.

## Milestone 7 — Company intelligence ✅
- [x] Public data aggregation for companies
- [x] AI-generated company summaries

Notes:
- Two real sources of "public data aggregation," both honestly scoped:
  - **Wikipedia** (`providers/company_data_providers/wikipedia_provider.py`):
    a direct title lookup against Wikipedia's public REST summary API, no
    key. Deliberately does NOT do a disambiguation/search step - a
    best-guess title match could attach the wrong company's facts to a job
    posting (e.g. matching the wrong "Square"), which is worse than
    returning nothing. Companies whose Wikipedia article title doesn't
    match their job-posting name exactly come back `found=False` rather
    than a wrong result. A real search-based lookup would improve hit rate
    and is a natural follow-up, not built here.
  - **Job-posting-derived tech stack** (`services/company_intelligence.py`):
    scans a company's own already-ingested job descriptions against a
    curated keyword list. Purely local, no network call, always available -
    arguably the most directly relevant signal available, since it's the
    company's own hiring language rather than a third party's guess.
- **Explicitly did NOT implement AI-generated `salary_insights`.** Doing so
  via an LLM with no real salary data source behind it would mean
  fabricating compensation figures - exactly the kind of hallucination that
  could mislead someone's real financial decisions. That field stays null
  until a real salary data source (Levels.fyi, Glassdoor-style aggregation,
  etc.) is integrated; the frontend says so explicitly rather than hiding
  the gap.
- `culture_summary` and `reputation_summary` ARE AI-generated
  (`POST /companies/{id}/enrich`, same LLM-orchestrator pattern as
  Milestones 3/6), but both system prompts explicitly instruct the model to
  base output only on the signals it's given and to say so plainly when
  those signals are thin, rather than padding with generic or invented
  detail.
- Jobs now auto-link to a `Company` record on ingestion
  (`get_or_create_company`, case-insensitive name dedupe) -
  `Job.company_id` had existed unused since Milestone 1's scaffold; this is
  what finally populates it.
- A company-data-provider failure (network error, bad response) degrades to
  "no public data found" rather than 500ing the enrichment endpoint -
  verified this actually works end-to-end in this dev sandbox, where
  `en.wikipedia.org` isn't in the network egress allowlist, so every
  enrichment test run here genuinely exercises the failure path, not just a
  mocked one.
- New endpoints: `GET /companies`, `GET /companies/{id}`,
  `GET /companies/{id}/jobs`, `GET /companies/data-providers`,
  `POST /companies/{id}/enrich`.
- Frontend: new Companies page - list (auto-populated from job ingestion),
  detail view with an "Enrich" button, tech stack / culture / reputation
  display, open roles at that company, and an explicit note on why salary
  insights aren't shown.
- Tests: 14 new (Wikipedia provider found/404/disambiguation cases, company
  dedupe, tech-stack inference, enrichment's salary-insights guard,
  enrichment's graceful degradation when public data isn't found, full API
  flows), 88/88 total passing. Frontend typechecks clean.

## Milestone 8 — Browser-assisted applications ✅
- [x] Playwright integration for autofill on supported ATS platforms
- [x] Human-in-the-loop pause points (auth, CAPTCHA, ambiguous fields)

**Safety design (non-negotiable, not just documentation):**
- Always launches headed (visible), never headless - the user watches
  everything in real time on their own screen.
- Never attempts to solve a CAPTCHA - any CAPTCHA detected halts the
  session immediately.
- Never fills a password field or attempts authentication - any password
  input detected halts the session immediately, even if disguised by a
  confusing label (tested explicitly).
- **Never clicks the final Submit/Apply button, ever.** Once the form is
  filled as far as it safely can be, the session stops at
  `AWAITING_SUBMIT` - the human reviews and clicks Submit themselves in the
  real browser window. This is the mandatory last step of every session,
  not a fallback for edge cases.
- Only fills values the user already entered into their own CareerOps++
  profile/resume - nothing fetched from elsewhere, nothing invented.
- Defaults to NOT filling: an unrecognized required field pauses rather
  than guessing, since a wrong guess put into a real application is a much
  worse failure than an extra click to resume.

**Architecture:** the decision logic (which field is which, when to pause)
lives in `services/browser_automation/field_classifier.py` as pure
functions with zero Playwright dependency - fully unit-tested (16 tests,
including explicit safety-guard tests like "a password field is never
filled even if its label says something else"). The actual browser-driving
code (`playwright_driver.py`) calls into that logic but does the I/O
(`page.fill()`, `page.goto()`, etc.) itself.

**NOT LIVE-VERIFIED - said plainly, not glossed over:** `playwright_driver.py`
could not be executed end-to-end in this dev sandbox. `pip install
playwright` succeeds, but `playwright install chromium` (a ~150-300MB
browser binary download from `cdn.playwright.dev`) failed - that host isn't
in the sandbox's network egress allowlist, same category of limitation as
Voyage/Wikipedia earlier in this project. What IS verified: the API layer's
handling of a genuinely missing browser is tested against the real failure
(not a mock) - `POST /automation/sessions` correctly returns 503 with a
clear "run `playwright install chromium`" message and records an `error`
status in the audit log, because that's exactly what happens when this
runs in an environment without the browser binary installed.
**Before relying on this for a real application, manually verify it
against a live Greenhouse or Lever application form** - the field-label
detection logic in `_detect_fields` (matching an `<input>` to its
`<label>`) is the part most likely to need real-world tuning per ATS
platform.

**Known gap, later closed:** resumes in this app are stored as plain
text/markdown (`Resume.content`), and at the time this milestone shipped
there was no PDF/DOCX export pipeline - `profile_builder.py` wrote raw
text to a temp `.txt` file, which most real ATS resume-upload fields
reject. **Fixed in a follow-up pass** - see "Resume PDF export" below.

**What was added along the way:**
- `User` gained `phone`, `linkedin_url`, `portfolio_url` fields - needed
  for autofill to have real data to work with. New `GET/PATCH /me`
  endpoints and a Profile page expose them.
- `ApplicationAutomationSession` model is a durable audit log (status,
  pause reason, filled-fields transparency log) - the live Playwright
  handle itself is process-local (in-memory registry in
  `session_manager.py`), so it can't survive a server restart; the DB row
  is what persists.
- Frontend: Dashboard's kanban cards gained an "Auto-fill application"
  button and inline status/pause/resume/close controls, with an explicit
  note whenever the browser genuinely isn't available.
- Tests: 16 (field classifier/fill-plan logic, including safety-critical
  cases) + 6 (automation API, exercising the real missing-browser path) +
  3 (profile endpoints) = 25 new, 113/113 total passing.

## Milestone 9 — Premium UX pass ✅
- [x] Command palette, keyboard shortcuts, dark/light mode, animations

Notes:
- Built a real design token system (`frontend/src/index.css`) rather than
  the generic AI-UI defaults - not cream+terracotta, not near-black+acid-
  green. Palette: deep indigo-violet accent (`#6C63FF` dark / `#5750E0`
  light) + warm amber for in-progress/momentum states, on a blue-tinted
  near-black (dark) or off-white (light) base. Type: Space Grotesk for
  headers (geometric character), IBM Plex Sans for body, IBM Plex Mono for
  data/shortcuts - a deliberately different pairing from the Inter-
  everywhere look most generated UIs reach for, and one with real
  developer-tool associations that fit "the VS Code of job hunting"
  positioning from the original spec.
- **Command palette (⌘K)** is the signature element - genuinely functional
  keyboard-driven navigation across every page
  (`components/CommandPalette.tsx`), not a decorative modal. Fuzzy-filters
  as you type, arrow-key navigable, Enter to go.
- Single-key "go to" shortcuts (`d`/`j`/`a`/`r`/`n`/`c`) for the most
  common destinations, disabled while typing in any input/textarea so they
  never fight with normal form use.
- Dark/light mode via a `data-theme` attribute + CSS custom properties,
  persisted to `localStorage`, defaulting to the OS preference
  (`prefers-color-scheme`) on first visit.
- Kanban cards on the Dashboard get a left-border color coded by pipeline
  stage (`.stage-saved`, `.stage-applied`, etc.) - a structural device that
  encodes real state, following the frontend-design skill's guidance that
  structure should mean something rather than decorate.
- Motion is deliberately restrained: palette open/close fade+scale,
  button/card hover transitions, nothing ambient or attention-grabbing -
  and `prefers-reduced-motion` is respected globally (all animation/
  transition durations collapse to ~0 for users who've asked for that).
- Visible keyboard focus (`:focus-visible` outline) on every interactive
  element, per the skill's "quality floor" requirement.
- Every hardcoded hex color found across the existing pages was migrated
  to reference the token system, so theme switching actually applies
  everywhere rather than leaving stray hardcoded-dark-mode colors behind
  in light mode.
- **Scope note:** this pass touched the shared shell (colors, type,
  buttons/inputs/cards globally, the palette, the theme toggle) and fixed
  color-token usage across every page. It did NOT do a full per-page
  layout/interaction redesign of each of the 8 pages - that's still fairly
  utilitarian inline-flexbox layout, functional but not the
  Linear/Raycast/Vercel/Notion-level interaction polish (drag-and-drop
  kanban, animated list reordering, etc.) the original spec envisions.
  That's a reasonable next increment, not claimed as done here.
- Frontend production build (`npm run build`) verified clean.

## Follow-up: Resume PDF export ✅

Closes the known gap from Milestone 8 above. `services/resume_export.py`
renders a Resume's stored markdown-lite content into a real PDF via
`reportlab` - a simple line-based parser (`# `/`## ` headings, `- `/`* `
bullets, `**bold**`/`*italic*` inline styles, blank-line paragraph breaks),
not a full CommonMark implementation, but sufficient for the AI-generated
resume content this app produces.

- New endpoint: `GET /resumes/{id}/export.pdf` - downloads any resume
  version as a PDF, with a proper `Content-Disposition` header.
- `services/browser_automation/profile_builder.py` now generates a real
  PDF for autofill's resume-upload field instead of a `.txt` file.
- Explicitly NOT a resume template/design system - output is plain,
  readable, single-column. A real "resume builder" with visual templates
  is a separate, larger feature than this fix attempts to be.
- Tests: 5 for the export function itself (including a real check that
  `<`, `>`, `&` in resume content don't break reportlab's XML-based
  Paragraph parser - verified by actually parsing the output PDF with
  `pypdf` and checking the extracted text, not just checking for
  non-empty bytes) + 2 for `profile_builder` generating a real `.pdf` file
  + 1 API test, 120/120 total passing.

## Follow-up still needed

- `playwright_driver.py` (Milestone 8) still has never been run against a
  real browser - this dev sandbox can't download the Chromium binary from
  `cdn.playwright.dev`. Manually verify against a real Greenhouse or Lever
  application form before trusting it.
- Real auth / multi-user support, replacing the single-local-user shim.
- Job sources from the backlog below, picked based on what's actually
  relevant to a real job search rather than built speculatively.
- Per-page interaction polish beyond Milestone 9's shared design system.


- [ ] Plugin marketplace
- [ ] Optional cloud sync
- [ ] Browser extension, mobile companion
