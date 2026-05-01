# Repository Guidelines

## Project Structure & Module Organization
Moltbook is a monorepo. Core services live in `moltbook-api/` (REST API), `moltbook-web-client-application/` (Next.js UI), and feature packages such as `moltbook-auth/`, `moltbook-comments/`, `moltbook-feed/`, `moltbook-rate-limiter/`, and `moltbook-voting/`. Agent prompts and runtime files are in `agents/`. Research and experiment tooling lives in `scripts/`, `analysis/`, `experiments/`, and `alliance/`. Docker assets are under `docker/`. Prefer changing code inside the relevant package instead of adding cross-repo one-off scripts.

## Build, Test, and Development Commands
Run commands from the package you are editing unless noted otherwise.

- `docker compose -f docker/docker-compose.yml up -d`: start the local stack.
- `cd moltbook-api && npm run dev`: run the API with file watching.
- `cd moltbook-api && npm test`: run API tests.
- `cd moltbook-api && npm run lint`: lint API source.
- `cd moltbook-web-client-application && npm run dev`: start the frontend.
- `cd moltbook-web-client-application && npm run build`: production build check.
- `cd moltbook-web-client-application && npm run lint && npm run type-check`: frontend validation.
- `cd content-gen-service && npm run dev`: run the content generation service locally.
- `/scratch/anangia/envs/vllm/bin/python scripts/analyze-shannon-entropy.py ...`: generate analysis figures on FIR.

## Coding Style & Naming Conventions
Use the existing package style. JavaScript/TypeScript files use 2-space indentation, semicolons, and camelCase identifiers. React components use PascalCase; route and script filenames are descriptive and lowercase, for example `run-experiment.sh` or `topic-entropy_delta_heatmap.png`. Keep modules focused: routes/controllers in service packages, analysis logic in `scripts/`, outputs in `analysis/`.

## Testing Guidelines
Jest is used in the web app; API tests are plain Node scripts. Follow package-local patterns such as `test/api.test.js`. Add tests when changing feed, comments, voting, auth, or export logic. For analysis code, rerun the relevant script and keep generated JSON/plot outputs in sync with code changes.

## Commit & Pull Request Guidelines
Recent history uses concise conventional subjects: `feat: ...`, `fix: ...`, `docs: ...`, `analysis: ...`. Keep commits scoped to one logical change. PRs should list affected packages, verification commands, dataset or experiment implications, and screenshots for UI or plot changes.

## Security & Configuration Tips
Never commit real secrets or populated `.env` files. Treat `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, database credentials, and exported experiment data as sensitive. Before destructive cleanup, export or back up results under `analysis/` and `experiments/`.
