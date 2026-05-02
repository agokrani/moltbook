#!/usr/bin/env python3
"""Resume an incomplete entropy-collapse run for additional duration.

Loads the historical postgres dump, rotates each agent's API key (the originals
are SHA-256 hashed and unrecoverable), pre-populates each agent container's
credentials volume so registration is skipped, and runs the agents for the
remaining duration. Currently supports n10 only.
"""
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
EMPTY_WORLD_POSTS = "/app/experiments/entropy-collapse/world-posts-empty.jsonl"

# Greek-letter agent ordering must match the dump's agent_<greek> sequence.
GREEK_ORDER = [
    "alpha", "beta", "gamma", "delta", "epsilon",
    "zeta", "eta", "theta", "iota", "kappa",
    "lambda", "mu", "nu", "xi", "omicron",
    "pi", "rho", "sigma", "tau", "upsilon",
    "phi", "chi", "psi", "omega",
    # n30 extension — names verified against original cluster n30 exports
    # (experiments/entropy-collapse/data/gemini-flash-lite/n30/*/agents.jsonl)
    "selene", "helios", "nyx", "atlas", "orion", "phoenix",
]


def agents_for_scale(scale: str):
    """Return [(idx, name, vol_suffix), ...] for the given scale.

    `name` here is the conventional baseline name (`ranking_<greek>`); the
    runner auto-detects the actual prefix from the DB so the dump's
    `agent_<greek>` rows are also matched.
    """
    n = int(scale[1:])
    if n > len(GREEK_ORDER):
        sys.exit(f"scale {scale} requested but only {len(GREEK_ORDER)} greek names defined")
    return [
        (i + 1, f"ranking_{GREEK_ORDER[i]}", f"ranking_agent{i + 1}_config")
        for i in range(n)
    ]


# Compose overlay per scale. The base parallel file is always included.
OVERLAY_FOR_SCALE = {
    "n10": "docker/docker-compose.civiclens-conspiracy-parallel.yml",
    "n20": "docker/docker-compose.civiclens-conspiracy-parallel-n20.yml",
    "n30": "docker/docker-compose.civiclens-conspiracy-parallel-n30.yml",
}

CONDITION_MODEL = {
    "mag0":     "openai/gpt-5",
    "mag1":     "openai/gpt-5",
    "mag5":     "google/gemini-3.1-flash-lite-preview",
    "mag25":    "google/gemini-3.1-flash-lite-preview",
    "dom-agi":  "google/gemini-3.1-flash-lite-preview",
    "dom-tech": "google/gemini-3.1-flash-lite-preview",
}

# Per-run remaining duration in minutes (60 - last_post_min from incomplete_runs.md)
REMAINING_MIN = {
    "ec-mag0-run04":         17,
    "ec-mag1-run04":         17,
    "ec-dom-agi-n10-run01":  35,
    "ec-dom-tech-n10-run01": 20,
    "ec-dom-agi-n20-run01":  34,
    "ec-mag5-n20-run01":     34,
    "ec-mag25-n30-run01":    34,
    "ec-mag5-n30-run01":     34,
}


def gen_api_key() -> str:
    return "moltbook_" + secrets.token_hex(32)


def hash_key(k: str) -> str:
    return hashlib.sha256(k.encode()).hexdigest()


def parse_run(name: str):
    """Returns (condition, scale) e.g. ec-dom-agi-n20-run01 -> ('dom-agi', 'n20')."""
    parts = name.split("-")
    if parts[0] != "ec":
        sys.exit(f"Run name must start with 'ec-': {name}")
    parts = parts[1:]
    scale = "n10"
    cond_parts = []
    for p in parts:
        if p.startswith("n") and p[1:].isdigit():
            scale = p
            break
        if p.startswith("run"):
            break
        cond_parts.append(p)
    return "-".join(cond_parts), scale


def find_run_dir(name: str):
    cond, scale = parse_run(name)
    candidates = [
        PROJECT / "experiments/entropy-collapse/data" / scale / name,
        PROJECT / "experiments/entropy-collapse/data/gemini-flash-lite" / scale / name,
    ]
    for p in candidates:
        if p.is_dir():
            for fname in ("database.sql", "database-final.sql"):
                dump = p / fname
                if dump.exists():
                    return p, cond, scale, dump
    sys.exit(f"Run dir or database dump not found for {name}; searched: {[str(c) for c in candidates]}")


def compose_files_for_scale(scale: str):
    overlay = OVERLAY_FOR_SCALE.get(scale)
    if overlay is None:
        sys.exit(f"No compose overlay registered for scale {scale}")
    if not (PROJECT / overlay).exists():
        sys.exit(f"Overlay file missing: {overlay}")
    return ["-f", "docker/docker-compose.parallel.yml", "-f", overlay]


def compose_cmd(project: str, env_file: str, *args, env=None, scale: str = "n10"):
    """Build a docker compose command with the right project + env-file + project dir."""
    cmd = ["docker", "compose",
           "--project-directory", str(PROJECT),
           "-p", project,
           "--env-file", env_file,
           *compose_files_for_scale(scale), *args]
    return cmd


def run(cmd, env=None, check=True, capture=False, input=None):
    full_env = {**os.environ, **(env or {})}
    proc = subprocess.run(cmd, env=full_env, check=check, capture_output=capture,
                          text=True, input=input, cwd=str(PROJECT))
    return proc


def psql_exec(project: str, env_file: str, env: dict, sql: str = None,
              file_path: str = None, capture=False, scale: str = "n10"):
    """Run psql inside the postgres container."""
    cmd = compose_cmd(project, env_file, "exec", "-T", "postgres",
                      "psql", "-U", "moltbook", "-d", "moltbook", "-v", "ON_ERROR_STOP=1",
                      scale=scale)
    if sql:
        cmd += ["-c", sql]
    input_data = open(file_path).read() if file_path else None
    return run(cmd, env=env, check=False, capture=True, input=input_data)


def write_credentials(volume_name: str, api_key: str, agent_name: str):
    creds = json.dumps({"api_key": api_key, "agent_name": agent_name})
    # Use python -c via alpine to avoid quoting issues
    script = (
        "import json,os; "
        "os.makedirs('/cfg', exist_ok=True); "
        f"open('/cfg/credentials.json','w').write({creds!r})"
    )
    run(["docker", "run", "--rm", "-v", f"{volume_name}:/cfg",
         "python:3-alpine", "python", "-c", script],
        check=True, capture=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_name")
    ap.add_argument("--duration-min", type=int, default=None,
                    help="Override remaining duration in minutes")
    ap.add_argument("--slot", type=int, default=0,
                    help="Parallel slot index (0=default ports, 1+=shifted by 100)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    run_dir, cond, scale, db_dump = find_run_dir(args.run_name)
    if scale not in OVERLAY_FOR_SCALE:
        sys.exit(f"Unsupported scale {scale} (registered: {sorted(OVERLAY_FOR_SCALE)})")
    if cond not in CONDITION_MODEL:
        sys.exit(f"Unknown condition: {cond}")
    agents = agents_for_scale(scale)
    n_agents = len(agents)

    duration_min = args.duration_min or REMAINING_MIN.get(args.run_name, 17)
    duration_sec = duration_min * 60
    model = CONDITION_MODEL[cond]
    project = f"resume-{args.run_name}".replace("_", "-")
    env_file = str(PROJECT / ".env.entropy-resume")
    out_dir = PROJECT / "exports" / f"{args.run_name}-resumed"
    out_dir.mkdir(parents=True, exist_ok=True)

    api_port = 4000 + args.slot * 100
    pg_port = 5432 + args.slot * 100
    redis_port = 6379 + args.slot * 100
    env = {
        "OPENROUTER_MODEL": model,
        "EXPERIMENT_NAME": f"{args.run_name}-resumed",
        "EXPERIMENT_MODE": "C",
        "EXPERIMENT_RANKING_ENABLED": "true",
        "WORLD_POSTS_FILE": EMPTY_WORLD_POSTS,
        "WORLD_POST_INTERVAL_MS": "999999999",
        "HOST_API_PORT": str(api_port),
        "HOST_PG_PORT": str(pg_port),
        "HOST_REDIS_PORT": str(redis_port),
        "HEARTBEAT_INTERVAL": "60s",
    }

    print(f"=== Resume {args.run_name} ===")
    print(f"  condition:     {cond}")
    print(f"  scale:         {scale}")
    print(f"  model:         {model}")
    print(f"  remaining:     {duration_min} min")
    print(f"  project:       {project}")
    print(f"  dump:          {db_dump}  ({db_dump.stat().st_size:,} bytes)")
    print(f"  out:           {out_dir}")
    if args.dry_run:
        return

    teardown_cmd = compose_cmd(project, env_file, "down", "-v", "--remove-orphans", scale=scale)

    try:
        # 1. Teardown any prior state with this project name
        print("\n[1/8] Teardown prior state...")
        run(teardown_cmd, env=env, check=False, capture=True)

        # 2. Bring up postgres + redis
        print("\n[2/8] Starting postgres + redis...")
        run(compose_cmd(project, env_file, "up", "-d", "postgres", "redis", scale=scale),
            env=env, check=True)

        # Wait for postgres healthy
        for i in range(30):
            r = run(compose_cmd(project, env_file, "ps", "postgres", "--format", "json", scale=scale),
                    env=env, check=False, capture=True)
            if '"healthy"' in r.stdout or '"running"' in r.stdout:
                if i > 5:  # give schema.sql init time to complete
                    break
            time.sleep(2)

        # 3. Reset schema, then restore dump
        print("\n[3/8] Resetting schema and restoring dump...")
        r = psql_exec(project, env_file, env, scale=scale,
                      sql="DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        if r.returncode != 0:
            print(f"  schema reset stderr: {r.stderr[:500]}")
            sys.exit(1)
        r = psql_exec(project, env_file, env, scale=scale, file_path=str(db_dump))
        if r.returncode != 0:
            print(f"  restore stderr: {r.stderr[:500]}")
            sys.exit(1)
        # Bring restored schema forward to match current API expectations.
        # The March 2026 dumps predate the source-citation feature; without
        # this the API returns 500 on every feed/post call.
        r = psql_exec(project, env_file, env, scale=scale,
                      sql="ALTER TABLE posts ADD COLUMN IF NOT EXISTS source_url TEXT;")
        if r.returncode != 0:
            print(f"  schema-forward stderr: {r.stderr[:300]}")
        # Sanity check
        r = psql_exec(project, env_file, env, scale=scale,
                      sql="SELECT COUNT(*) AS posts FROM posts; SELECT COUNT(*) AS agents FROM agents;",
                      capture=True)
        print(f"  restored DB:\n{r.stdout}")

        # 4. Rotate API keys for each historical agent and prep credentials volumes.
        # Detect the agent-name prefix used in this dump — GPT-5 dumps use
        # 'ranking_<greek>', Gemini dumps use 'agent_<greek>'. The volume layout
        # (ranking_agent<N>_config) and the credentials.json contents stay the
        # same; only the WHERE clause for the DB UPDATE has to track the prefix.
        print(f"\n[4/8] Rotating API keys + writing credentials volumes ({n_agents} agents)...")
        r = psql_exec(project, env_file, env, scale=scale,
                      sql="SELECT name FROM agents WHERE name NOT LIKE 'civiclens%' ORDER BY name;",
                      capture=True)
        db_names = [n.strip() for n in r.stdout.splitlines() if n.strip()]
        prefix = None
        for candidate in ("ranking_", "agent_"):
            if any(n.startswith(candidate) for n in db_names):
                prefix = candidate
                break
        if prefix is None:
            sys.exit(f"Could not detect agent-name prefix from DB names: {db_names}")
        if len(db_names) != n_agents:
            print(f"  [WARN] DB has {len(db_names)} non-civiclens agents, expected {n_agents}")
        print(f"  detected prefix: {prefix!r}  (agents in DB: {len(db_names)})")
        for idx, name, vol_suffix in agents:
            db_name = name if name.startswith(prefix) else prefix + name.split("_", 1)[1]
            key = gen_api_key()
            kh = hash_key(key)
            volume_name = f"{project}_{vol_suffix}"
            r = psql_exec(project, env_file, env, scale=scale,
                          sql=f"UPDATE agents SET api_key_hash='{kh}' WHERE name='{db_name}' RETURNING name;",
                          capture=True)
            if r.returncode != 0 or "UPDATE 1" not in r.stdout:
                print(f"  [WARN] key rotate failed for {db_name}: rc={r.returncode} stdout={r.stdout[:200]} stderr={r.stderr[:200]}")
            run(["docker", "volume", "create", volume_name], check=False, capture=True)
            write_credentials(volume_name, key, db_name)
            print(f"  [keyed] {db_name:20} → vol={volume_name}")

        # 5. Bring up API
        print("\n[5/8] Starting API...")
        run(compose_cmd(project, env_file, "up", "-d", "api", scale=scale), env=env, check=True)
        api_ready = False
        for i in range(40):
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                f"http://localhost:{api_port}/api/v1/health"],
                               capture_output=True, text=True)
            if r.stdout.strip() == "200":
                api_ready = True
                break
            time.sleep(3)
        if not api_ready:
            sys.exit(f"API failed to become healthy on :{api_port}")
        print("  API healthy")

        # 6. Bring up agents.
        # OpenClaw gateway init (canvas mount, bonjour, websocket bind) needs
        # ~1-2s of dedicated CPU per agent. Booting 20+ in parallel saturates
        # a typical 10-CPU host and the event loops never finish init — they
        # spin in R state without ever firing a heartbeat. So we build all
        # images up-front (fast, parallel-safe) and then start containers
        # serially with a 5s stagger.
        print(f"\n[6/8] Starting {n_agents} agents...")
        agent_services = [f"civiclens-ranking-{i}" for i, _, _ in agents]

        # Pre-build images (no --no-start in compose v1; use build subcommand)
        print(f"  pre-building {n_agents} images...")
        run(compose_cmd(project, env_file, "build", *agent_services, scale=scale),
            env=env, check=True)

        if n_agents >= 20:
            stagger_sec = 5
            print(f"  staggered startup ({stagger_sec}s between containers)...")
            for svc in agent_services:
                run(compose_cmd(project, env_file, "up", "-d", "--no-build", svc, scale=scale),
                    env=env, check=True, capture=True)
                time.sleep(stagger_sec)
        else:
            run(compose_cmd(project, env_file, "up", "-d", "--no-build", *agent_services, scale=scale),
                env=env, check=True)
        time.sleep(15)

        # 7. Run for remaining duration with periodic post-count
        print(f"\n[7/8] Resuming agents for {duration_min} minutes...")
        start = time.time()
        check_interval = 120  # report every 2 minutes
        while True:
            elapsed = time.time() - start
            if elapsed >= duration_sec:
                break
            time.sleep(min(check_interval, duration_sec - elapsed))
            r = psql_exec(project, env_file, env, scale=scale,
                          sql="SELECT COUNT(*) FROM posts WHERE created_at > NOW() - INTERVAL '5 minutes';",
                          capture=True)
            recent = r.stdout.strip().split('\n')[-2].strip() if r.returncode == 0 else "?"
            elapsed_min = (time.time() - start) / 60
            print(f"  [{elapsed_min:5.1f}min/{duration_min}min] posts in last 5min: {recent}")

        # Capture container logs before teardown
        print("\n  Capturing container logs...")
        for svc in ["api"] + agent_services:
            r = run(compose_cmd(project, env_file, "logs", "--no-color", "--tail=2000", svc, scale=scale),
                    env=env, check=False, capture=True)
            (out_dir / f"docker-logs-{svc}.txt").write_text(r.stdout + r.stderr)

        # 8. Run export
        print(f"\n[8/8] Exporting to {out_dir}...")
        export_env = {
            **env,
            "COMPOSE_PROJECT_NAME": project,
            "COMPOSE_OVERLAY": OVERLAY_FOR_SCALE[scale],
            "SLOT_ENV_FILE": env_file,
            "MOLTBOOK_API_URL": f"http://localhost:{api_port}/api/v1",
            "HOST_API_PORT": str(api_port),
        }
        run([str(PROJECT / "scripts/export-experiment-parallel.sh"),
             f"{args.run_name}-resumed"],
            env=export_env, check=False)

    finally:
        print("\n[teardown] Stopping containers + removing volumes...")
        run(teardown_cmd, env=env, check=False, capture=True)
        print(f"=== Done. Output: {out_dir} ===")


if __name__ == "__main__":
    main()
