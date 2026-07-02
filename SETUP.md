# CareerOps++ — Setup Guide

This is the single place that answers "what do I need to fill in, and how
do I actually run this thing." Everything here is also scattered in
docstrings and ROADMAP.md notes throughout the codebase — this file just
collects it in one spot.

**The most important fact: CareerOps++ runs with zero API keys.** Every
external integration (LLM providers, some job providers, the embedding
provider) has a free, keyless fallback so the app is fully usable out of
the box. Keys only unlock *better* results, not basic functionality.

---

## 1. Prerequisites

- **Python 3.12** (or close to it — 3.11+ should work)
- **Node.js 20** (or close to it — 18+ should work)
- **git**

No database server to install — SQLite is a file, created automatically.

---

## 2. Clone and install

```bash
git clone https://github.com/PharateSwapnil/CareerOps.git
cd CareerOps

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend (separate terminal, or after deactivating the venv)
cd ../frontend
npm install
```

---

## 3. Environment file (`backend/.env`)

Copy the template and fill in only what you want:

```bash
cd backend
cp .env.example .env
```

Every single variable below is **optional**. Leave any of them blank and
that specific feature falls back to a free/local/stub behavior instead of
erroring — nothing in the app requires a paid key to function.

### Core (usually leave as-is)

| Variable | Default | Notes |
|---|---|---|
| `DEBUG` | `true` | Verbose SQL logging; set `false` for anything resembling production |
| `DATABASE_URL` | `sqlite:///./data/careerops.db` | Local-first SQLite file, created automatically |

### AI features — resume optimization, cover letters, networking messages, company summaries

Without any key here, these features work using a **stub provider** that
echoes back placeholder text — good for confirming the plumbing works, not
useful for real output. Configure **either** key below (or both, for
fallback) to get real AI-generated content.

| Variable | Where to get it | Free tier? |
|---|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys | No free tier, but usage is pay-as-you-go and cheap for personal use |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys | Yes, generous free tier |

The fallback order is Claude → Groq → stub (configurable via
`Settings.llm_provider_priority` in `backend/app/core/config.py` if you
want to change it — no env var for this one, it's a code-level default).

**Two keys exist in the settings but have no working provider behind them
yet** — `OPENROUTER_API_KEY` and `GEMINI_API_KEY` are placeholders for
future providers (see `docs/ROADMAP.md`), not functional today. Setting
them does nothing.

### Job discovery — most sources need nothing

9 of the 10 job providers (Greenhouse, Lever, Ashby, Arbeitnow, Remotive,
RemoteOK, Jobicy, We Work Remotely, Remote.co) are public and keyless —
they work immediately, no signup. One requires a free key:

| Variable | Where to get it | Free tier? |
|---|---|---|
| `ADZUNA_APP_ID` | [developer.adzuna.com](https://developer.adzuna.com) | Yes, free signup |
| `ADZUNA_APP_KEY` | same signup, issued alongside the App ID | Yes |

Without these two, the Adzuna provider just returns an empty list instead
of erroring — pick it from the Jobs page provider dropdown and it'll no-op
until you add a key.

### Semantic search — works immediately, better with a key

| Variable | Default | Notes |
|---|---|---|
| `EMBEDDING_DEFAULT_PROVIDER` | `hashing` | Free, local, zero-setup. Does lexical/keyword-overlap matching, not true semantic understanding — see caveat below |
| `VOYAGE_API_KEY` | (blank) | Set this **and** `EMBEDDING_DEFAULT_PROVIDER=voyage` for real neural embeddings |

Get a Voyage key at [dashboard.voyageai.com](https://dashboard.voyageai.com)
(free tier available). Without it, semantic search still works, but it
won't reliably connect e.g. a "Snowflake, Databricks, PySpark" search to an
"Analytics Engineer" posting unless those exact words appear in the text —
that cross-terminology matching is specifically what Voyage's real
embeddings add.

### Browser-assisted applications — no API key, but a separate download

Milestone 8's autofill feature needs a real browser binary, which is
**not** installed by `pip install` alone:

```bash
cd backend
source .venv/bin/activate
playwright install chromium
```

This downloads ~150-300MB from Microsoft's CDN. If your network blocks
that domain (as this project's own dev sandbox does — see
`docs/ROADMAP.md`), the feature will return a clear error explaining what's
missing rather than crashing, and everything else in the app keeps working.

**Important, not just a formality:** this feature was written but never
run against a real browser or a real application form during development
(same network restriction). Before trusting it with a real job
application, test it once yourself against a real Greenhouse or Lever
posting and watch what it does.

---

## 4. Running it

Two processes, two terminals:

```bash
# Terminal 1 — backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
# → http://localhost:8000  (API docs at /docs)

# Terminal 2 — frontend
cd frontend
npm run dev
# → http://localhost:5173
```

Open `http://localhost:5173`. That's the whole app.

### First things to do once it's running

1. **Profile page** — fill in your name, email, phone, LinkedIn, portfolio.
   This is what autofill (Milestone 8) uses; nothing else needs it.
2. **Jobs page** — pick a provider (try `greenhouse` or `remotive`, both
   keyless) and click Fetch. Jobs get auto-embedded and auto-linked to
   Company records as they're ingested.
3. **⌘K / Ctrl+K** anywhere opens the command palette.

### Verifying it's healthy

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok", "service": "CareerOps++ API"}
```

### Running the test suite

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

Should show `120 passed`. Tests use an isolated in-memory database — your
real `data/careerops.db` is never touched by running tests.

---

## 5. Quick reference — what's already fully functional right now, zero config

- Job discovery from 9 keyless sources + semantic search (local embeddings)
- Application pipeline tracking with an enforced status state machine
- Resume versioning, diffing, rollback, **and PDF export**
- Networking CRM with follow-up reminders
- Company records auto-created from job postings, with local tech-stack
  inference (no key needed — Wikipedia enrichment and AI summaries need
  network/keys, tech-stack inference from your own ingested jobs doesn't)
- The full UI: dashboard, command palette, dark/light mode, keyboard
  shortcuts

## 6. Quick reference — what needs a key/setup step to unlock

| Feature | Needs |
|---|---|
| Real AI text (not stub placeholders) | `ANTHROPIC_API_KEY` or `GROQ_API_KEY` |
| Adzuna job listings | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` |
| Real neural semantic search | `VOYAGE_API_KEY` + `EMBEDDING_DEFAULT_PROVIDER=voyage` |
| Wikipedia company enrichment | Just needs outbound network access — no key |
| Browser-assisted autofill | `playwright install chromium` (no key, but a download) |

Everything else in this table has a working fallback if you skip it.
