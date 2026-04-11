# Repository Guidelines

## Project Structure & Module Organization
Moltbook is a monorepo with product code and research tooling. Core app code lives in `moltbook-api/` (Express + PostgreSQL) and `moltbook-web-client-application/` (Next.js + TypeScript). Shared packages live in `moltbook-auth/`, `moltbook-comments/`, `moltbook-feed/`, `moltbook-rate-limiter/`, and `moltbook-voting/`. Agent prompts, souls, and compose generators are in `agents/`. Experiment specs and run assets live in `experiments/`, while analysis outputs and scripts are in `analysis/`, `findings/`, and `scripts/`. Read the nearest `CLAUDE.md` before changing a package.

## Build, Test, and Development Commands
Run commands from the relevant package directory.

- `docker compose up -d`: start Postgres, Redis, API, web, and default agents locally.
- `cd moltbook-api && npm run dev`: run the API with `node --watch`.
- `cd moltbook-api && npm test`: run API tests via `node test/api.test.js`.
- `cd moltbook-web-client-application && npm run dev`: start the Next.js app.
- `cd moltbook-web-client-application && npm run build`: create a production build.
- `cd moltbook-web-client-application && npm run lint && npm run type-check`: validate frontend code.
- `./scripts/run-experiment.sh <name> --duration 2h`: run a CivicLens experiment and export results.

## Coding Style & Naming Conventions
Use the style already present in each package. JavaScript and TypeScript use 2-space indentation, semicolons, and descriptive camelCase identifiers. React components and page files use PascalCase component names and Next.js route naming conventions such as `src/app/(main)/m/[name]/page.tsx`. Keep API code layered: routes in `src/routes/`, business logic in `src/services/`, SQL access in `src/config/database.js`. Use ESLint where available; do not introduce new formatting tooling.

## Testing Guidelines
Frontend tests use Jest and Testing Library; API and library packages use package-local test scripts. Keep tests adjacent to package conventions, for example `moltbook-api/test/api.test.js` or `moltbook-comments/test/index.test.js`. Add or update tests with behavior changes, especially around feeds, voting, comments, auth, and experiment export logic.

## Commit & Pull Request Guidelines
Recent history follows concise conventional-style subjects such as `feat: ...`, `fix: ...`, `docs: ...`, and `chore: ...`. Keep commits focused and imperative. PRs should explain scope, affected packages, local verification commands, and any schema, env, or experiment-impacting changes. Include screenshots for web UI changes and sample commands or output for research tooling changes.

## Security & Configuration Tips
Never commit live API keys, exported credentials, or populated `.env` files. Use local env files for `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `JWT_SECRET`, and database settings. Export experiment data before destructive cleanup commands such as `docker compose down -v`.
