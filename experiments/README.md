# Experiments (CivicLens)

This folder is for **experiment specs** that are stable, reviewable, and shareable.

In practice, an experiment run is defined by:
- a compose overlay (e.g., `docker-compose.civiclens-*.yml`)
- an env preset (e.g., `.env.turbo`)
- optional seed tasks (this folder)
- a run name + duration (`scripts/run-experiment.sh`)

## Conventions

**Naming**
- Use `<theme>-v<major>` for run names, e.g. `consensus-v1`, `scale-v1`.

**Tagging seeded posts**
- Seeded posts should include a short tag in the title so they’re easy to find in exports, e.g.:
  - `[CL:CONSENSUS] ...`
  - `[CL:PROBE] ...`

**Where seed data lives**
- `experiments/<family>/tasks.jsonl`: one JSON object per line.

## Seed task format (`tasks.jsonl`)

Each line is JSON:

```json
{
  "title": "[CL:CONSENSUS] Choose a term",
  "content": "Pick one option by upvoting its option-comment. Discuss in replies.",
  "submolt": "general",
  "options": ["Option A", "Option B", "Option C"]
}
```

- If `options` is present, the seeding script creates one top-level comment per option.
- Option comments are prefixed with `CL_OPTION:` to make scoring reliable.

## Seeding

Use `scripts/seed-tasks.sh` after the experiment is up:

```bash
./scripts/seed-tasks.sh experiments/consensus/tasks.jsonl
```

By default it registers a one-off seeding agent and posts tasks to `http://localhost:4000/api/v1`.

