# CareerOps++ — The AI Career Operating System

CareerOps++ is an open-source, AI-powered Career Operating System that helps job seekers
discover opportunities, prepare high-quality applications, manage their professional
network, and grow their careers — all from one local-first, privacy-respecting platform.

> **Status:** Milestone 1 — project scaffold, core data model, and local-first storage.
> See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system design and
> [`docs/ROADMAP.md`](docs/ROADMAP.md) for what's built vs. planned.

## Monorepo layout

```
careerops/
├── backend/          FastAPI application (Python)
│   ├── app/
│   │   ├── core/            settings, config, security
│   │   ├── models/           SQLModel ORM entities (Job, Application, Resume, Contact, Company, User)
│   │   ├── schemas/          Pydantic request/response schemas
│   │   ├── db/                session/engine setup, migrations
│   │   ├── api/routes/        FastAPI routers
│   │   └── providers/
│   │       ├── job_providers/   pluggable job source adapters (Greenhouse, Lever, RSS, ...)
│   │       └── llm_providers/   pluggable LLM adapters (Groq, Claude, OpenRouter, Gemini, ...)
│   └── tests/
├── frontend/          React + TypeScript (Vite) application
│   └── src/
│       ├── pages/
│       ├── components/
│       └── routes/
├── docs/               architecture, roadmap, contribution docs
└── .github/workflows/  CI
```

## Quickstart

**For full setup instructions — every environment variable, which are
optional, where to get each API key, and step-by-step run instructions —
see [`SETUP.md`](SETUP.md).** The short version:

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API docs available at `http://localhost:8000/docs`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Philosophy

- **Local-first**: your career data lives in a local SQLite database by default. No
  forced cloud account, no data lock-in.
- **Plugin-based**: job providers and LLM providers are pluggable adapters behind a
  common interface, so the platform can grow without core rewrites.
- **Assistance, not deception**: browser automation assists with repetitive form-filling
  and pauses for human input on auth, CAPTCHAs, or ambiguous questions. It does not try
  to bypass platform protections.

## Contributing

This project is in early scaffolding. See `docs/ARCHITECTURE.md` before opening a PR —
it documents the plugin interfaces new providers must implement.

## License

MIT (see `LICENSE`).
