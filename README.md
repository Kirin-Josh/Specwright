# Specwright

Turn a software spec into a reviewed, traceable delivery plan, then push it to Linear.

Upload a .docx or .pdf spec. A pipeline of agents extracts the requirements, drafts milestones and tasks, and checks that every requirement is covered. You review and edit the plan, then sync it to Linear in one click.

## Stack
- **Web:** Next.js 16, TypeScript, Tailwind
- **API:** FastAPI, Anthropic SDK, Pydantic, ARQ + Redis
- **Data:** Appwrite (auth, storage, database)
- **Integrations:** Linear GraphQL API

## Quick start
All commands run from the repo root.

```bash
npm install            # installs root + apps/web
npm run setup:api      # uv sync for the API
npm run redis          # Redis via Docker
npm run dev            # web (3000) + api (8000) together
```

Copy `apps/api/.env.example` to `apps/api/.env` and add your keys first.

Other scripts: `npm run dev:web`, `npm run dev:api`, `npm run test:api`, `npm run lint`, `npm run build`.

See `docs/architecture.md` and `docs/milestones.md`.
