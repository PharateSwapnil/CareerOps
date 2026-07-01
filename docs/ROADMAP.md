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

## Milestone 2 — Job discovery (single provider)
- [ ] Implement a real `JobProvider` for Greenhouse's public job board API
- [ ] Job ingestion endpoint + background fetch job
- [ ] Deduplication logic (source_provider + raw_source_id)
- [ ] Basic job list UI in frontend

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
