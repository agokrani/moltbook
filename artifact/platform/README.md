# Controlled platform snapshot

The repository root is the controlled Moltbook fork used for the experiments. The seven services are Git submodules; their immutable URLs and commits are recorded in `submodules.lock.json`. Initialize exactly those pins with:

```bash
git submodule update --init --recursive
```

The paper-relevant tracked configuration is already in the release branch:

- `docker-compose.civiclens-ranking-parallel.yml`: parallel controlled-feed deployment.
- `scripts/run-entropy-collapse-experiments.sh`: experiment orchestration.
- `scripts/export-experiment-parallel.sh`: run export.
- `agents/HEARTBEAT-v2.1.md`: agent heartbeat/posting policy.
- `.env.example`: names of required settings, with placeholder values only.
- `experiments/entropy-collapse/world-posts-{empty,mag1,mag5,mag25,agi,tech}.jsonl`: the six starting-feed conditions.

Do not commit a populated `.env`, service credentials, raw Docker logs, database dumps, or local volumes. Provider APIs and model aliases can change; reproductions should record provider, resolved model version, run timestamp, and random seed in their run manifest.
