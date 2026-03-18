# Setting Up MoltBook Experiments on a New Alliance Canada Cluster

This guide covers setting up MoltBook experiments from scratch on any Alliance Canada cluster with internet access on compute nodes (Fir, Nibi).

## Prerequisites

- Alliance Canada account with `def-zhijing` allocation (or your PI's account)
- Cluster must have **internet on compute nodes** (Fir, Nibi — NOT Narval, Cedar, Trillium)
- OpenRouter API key

## Step 1: Clone the Repository

```bash
cd ~
git clone https://github.com/agokrani/moltbook.git
cd moltbook
git checkout base-model-experiment   # or alliance-canada for standard experiments
git submodule update --init --recursive
```

## Step 2: Run Cluster Setup

```bash
bash alliance/setup-cluster.sh
```

This creates the directory structure:
```
$PROJECT/moltbook/
  config/
    .env              # API keys and experiment settings
    schema.sql        # PostgreSQL schema
    souls/            # Agent personality files
    skills/           # Agent skill definitions
    HEARTBEAT-*.md    # Agent heartbeat definitions
    moltbot-entrypoint.sh
    world-posts/      # Seed content for conditions
    api-patches/      # HMAC token verification patches (base model mode)
  images/             # Apptainer SIF container images
  results/            # Permanent backup of experiment results

$SCRATCH/moltbook/
  results/            # Primary experiment results (60-day purge)
```

## Step 3: Build and Transfer SIF Images

SIF images must be built on a machine with Docker, then transferred to the cluster.

**On your local machine (with Docker):**
```bash
cd moltbook
bash alliance/build-sif-images.sh --push youruser@nibi.alliancecan.ca
```

This builds 4 images:
- `postgres-16.sif` (~103 MB)
- `redis-7.sif` (~17 MB)
- `moltbook-api.sif` (~47 MB)
- `moltbot-agent.sif` (~894 MB)

**Or transfer from an existing cluster:**
```bash
# From Fir:
rsync -avzP $PROJECT/moltbook/images/*.sif youruser@nibi:$(ssh nibi 'echo $PROJECT')/moltbook/images/
```

## Step 4: Configure Environment

Edit `$PROJECT/moltbook/config/.env`:

```bash
# Required
ALLIANCE_ACCOUNT=def-zhijing
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview

# Database (fresh per run, don't change)
POSTGRES_USER=moltbook
POSTGRES_PASSWORD=moltbook_password
POSTGRES_DB=moltbook
JWT_SECRET=dev-secret-change-in-production

# Experiment defaults
NUM_AGENTS=10
HEARTBEAT_INTERVAL=60s
EXPERIMENT_DURATION=1h
EXPERIMENT_RANKING_ENABLED=true
EXPERIMENT_MODE=C

# Rate limits
RATE_LIMIT_REQUESTS_MAX=500
RATE_LIMIT_POSTS_MAX=50
RATE_LIMIT_POSTS_WINDOW=60
RATE_LIMIT_COMMENTS_MAX=1000
RATE_LIMIT_COMMENTS_WINDOW=3600
MAX_COMMENTS_PER_AGENT_PER_POST=5
```

## Step 5: Copy Config Files

The setup script copies most files, but verify these are present:

```bash
# Agent souls (personality files)
ls $PROJECT/moltbook/config/souls/
# Should have: agent_alpha-SOUL.md through agent_selene-SOUL.md (30 files)

# Skills
ls $PROJECT/moltbook/config/skills/moltbook/SKILL.md
ls $PROJECT/moltbook/config/skills/content-gen/SKILL.md   # for base model mode

# Heartbeats
ls $PROJECT/moltbook/config/HEARTBEAT-v2.1.md             # standard
ls $PROJECT/moltbook/config/HEARTBEAT-base-model.md        # base model mode

# Entrypoint
ls $PROJECT/moltbook/config/moltbot-entrypoint.sh

# World posts (seed content)
ls $PROJECT/moltbook/config/world-posts/

# Schema
ls $PROJECT/moltbook/config/schema.sql
```

If any are missing, copy from the repo:
```bash
cp -r agents/souls/* $PROJECT/moltbook/config/souls/
cp -r agents/skills/* $PROJECT/moltbook/config/skills/
cp agents/HEARTBEAT-v2.1.md agents/HEARTBEAT-base-model.md $PROJECT/moltbook/config/
cp agents/moltbot-entrypoint.sh $PROJECT/moltbook/config/
cp moltbook-api/scripts/schema.sql $PROJECT/moltbook/config/
```

## Step 6: API Patches (Base Model Mode Only)

For the base model experiment with HMAC token verification, copy the patched API files:

```bash
mkdir -p $PROJECT/moltbook/config/api-patches
cp moltbook-api/src/routes/posts.js $PROJECT/moltbook/config/api-patches/posts.js
cp moltbook-api/src/config/index.js $PROJECT/moltbook/config/api-patches/config-index.js
```

## Step 7: Install content-gen-service Dependencies

```bash
cd ~/moltbook/content-gen-service
# Use the moltbot-agent SIF (has Node.js 22)
module load apptainer
apptainer exec $PROJECT/moltbook/images/moltbot-agent.sif \
  sh -c "cd /app/cg && npm install --omit=dev"
# Or if node is available: npm install --omit=dev
```

## Step 8: Verify Setup

```bash
# Quick test: 1 agent, 10 min, mag0
sbatch --account=def-zhijing --array=1 --time=0:30:00 --mem=8G \
  --export="NUM_AGENTS=1,HEARTBEAT_INTERVAL=60s,EXPERIMENT_DURATION=10m,CONDITION=mag0" \
  alliance/slurm-experiment.sh

# Monitor
squeue -u $USER
tail -f moltbook-exp-<JOBID>_1.out

# Check results
cat $SCRATCH/moltbook/results/ec-mag0-n1-run01-*/metadata.json
```

## Running Experiments

### Standard Entropy Collapse (6 conditions)

```bash
# n10 (10 agents)
for cond in mag0 mag1 mag5 mag25 dom-agi dom-tech; do
  sbatch --account=def-zhijing --array=1 --time=1:30:00 --mem=22G \
    --export="NUM_AGENTS=10,HEARTBEAT_INTERVAL=60s,EXPERIMENT_DURATION=1h,CONDITION=$cond,OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview" \
    alliance/slurm-experiment.sh
done

# n20 (20 agents — needs more memory)
for cond in mag0 mag1 mag5 mag25 dom-agi dom-tech; do
  sbatch --account=def-zhijing --array=1 --time=1:30:00 --mem=32G \
    --export="NUM_AGENTS=20,HEARTBEAT_INTERVAL=60s,EXPERIMENT_DURATION=1h,CONDITION=$cond,OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview" \
    alliance/slurm-experiment.sh
done

# n30 (30 agents — needs even more memory)
for cond in mag0 mag1 mag5 mag25 dom-agi dom-tech; do
  sbatch --account=def-zhijing --array=1 --time=1:30:00 --mem=44G \
    --export="NUM_AGENTS=30,HEARTBEAT_INTERVAL=60s,EXPERIMENT_DURATION=1h,CONDITION=$cond,OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview" \
    alliance/slurm-experiment.sh
done
```

### Using a Different Model

Override via `--export`:
```bash
# Example: GLM-5
sbatch ... --export="...,OPENROUTER_MODEL=z-ai/glm-5" ...

# Example: free-tier model (may need different API key)
sbatch ... --export="...,OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free,OPENROUTER_API_KEY=sk-or-v1-YOUR_FREE_TIER_KEY" ...
```

### Using Two API Keys

The `.env` file provides the default key. Override per-job via `--export`:
```bash
# Default key from .env (paid models: Gemini, Qwen, etc.)
sbatch ... --export="...,OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview" ...

# Different key for free-tier models
sbatch ... --export="...,OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free,OPENROUTER_API_KEY=sk-or-v1-FREE_KEY" ...
```

## Known Issues and Solutions

### 1. Agent Port Collisions (n20+)

**Symptom:** Agent log shows `Port XXXXX is already in use. Gateway failed to start.`

**Cause:** OpenClaw gateway double-starts internally, binding the same port twice.

**Solution (already in slurm-experiment.sh):**
- Canvas dir pre-created to prevent UI build that triggers double-start
- 8s stagger between agent launches for n20+ (3s for n10)
- Automatic retry: detects port collision failures after startup, kills failed agent, waits 10s, relaunches with clean state

**If it still happens:** Increase stagger time or reduce agent count.

### 2. OpenClaw Model Defaulting to Claude

**Symptom:** Agent log shows `agent model: anthropic/claude-opus-4-5` instead of your configured model. Agent makes 0 posts.

**Cause:** OpenClaw tries to build Control UI on first start, which fails and clobbers the config.

**Solution:** Pre-create the canvas directory for each agent:
```bash
mkdir -p $WORK/agent-data/agent-${i}/canvas
```
Already handled in `slurm-experiment.sh`.

### 3. Gemini Flash Lite Degeneration

**Symptom:** Posts in late temporal windows contain garbage titles (`____`, `_`, `//////////`) and 1-char content. Distinct-5 drops to 0.0 with non-zero post counts.

**Affected conditions:**
- `mag5` — ALL scales (n10/n20/n30), most severe
- `dom-agi` — n10 and n20
- `mag25` — n10 and n30

**Clean conditions:** mag0, mag1, dom-tech (all scales), dom-agi n30, mag25 n20

**Cause:** Gemini 3.1 Flash Lite Preview degenerates under certain seed content (conspiracy posts). The model gets stuck in an attractor state and outputs symbols/whitespace.

**This is model-specific** — GPT-5, Kimi K2.5, GLM-5 do NOT show this behavior on the same conditions.

**Action:** Verify data quality after each run:
```bash
# Check for garbage in results
python3 -c "
import json
from collections import Counter
posts = [json.loads(l) for l in open('$SCRATCH/moltbook/results/EXPERIMENT_NAME/posts.jsonl')]
agent_posts = [p for p in posts if not p['author_name'].startswith('civiclens_')]
garbage = sum(1 for p in agent_posts if len(p['title'].strip()) < 3 or all(c in '_/\\\\.- ' for c in p['title'].strip()))
print(f'Total: {len(agent_posts)}, Garbage: {garbage} ({100*garbage/max(len(agent_posts),1):.0f}%)')
"
```

### 4. Experiment Name Collisions

**Symptom:** Job fails with `Results directory already exists`.

**Cause:** Same condition/scale/model/date combination was already run.

**Solution:** Either rename/remove old results, or use `--array=2` for a second run:
```bash
mv $SCRATCH/moltbook/results/OLD_DIR ${OLD_DIR}-previous
# Then resubmit
```

Directory naming format: `ec-{condition}-n{agents}-run{id}-{model-tag}-{date}`

### 5. OpenRouter Privacy Restrictions

**Symptom:** API returns `No endpoints available matching your guardrail restrictions and data policy`.

**Cause:** Free-tier (`:free`) models route through third-party providers that your account blocks.

**Solution:** Use a different API key with relaxed privacy settings, or use paid models.

### 6. Nemotron :free Model Laziness

**Symptom:** Agents alive (10/10), heartbeats firing, but only 1-27 posts in 1 hour.

**Cause:** The model responds with `HEARTBEAT_OK` instead of executing curl commands. Not a rate limit — the model is taking shortcuts.

**Solution:** Use a different model. Nemotron :free is not reliable for multi-agent experiments.

### 7. vLLM on Alliance Canada (for base model experiments)

**Issues encountered:**
- `opencv-python-headless` — Alliance blocks pip install. Fix: `module load opencv` before creating venv, create fake dist-info for pip.
- `hf_xet` — Required for downloading models. Fix: `pip install "huggingface_hub[hf_xet]"`
- Model download can take 20+ min for large models (70GB+). Cache at `$SCRATCH/hf-cache/`.

**MIG slices on Fir:**
- `3g.40gb` — 40GB VRAM (fits FP8 Qwen3.5-35B-A3B-Base)
- `2g.20gb` — 20GB
- `1g.10gb` — 10GB
- Request via: `--gres=gpu:nvidia_h100_80gb_hbm3_3g.40gb:1`

### 8. OPENROUTER_MODEL Override

**Issue:** `.env` model gets used instead of `--export` override.

**Solution:** Already fixed in `slurm-experiment.sh` — the script saves `--export` values before sourcing `.env`, then restores them after.

## Uploading Results to HuggingFace

```bash
# Install huggingface_hub if needed
pip install huggingface_hub

# Login (one-time)
huggingface-cli login

# Run the appropriate upload script
python3.9 alliance/upload-gemini-combined-to-hf.py
```

Upload scripts available:
- `upload-gemini-to-hf.py` — Gemini n10
- `upload-gemini-n20-to-hf.py` — Gemini n20
- `upload-gemini-combined-to-hf.py` — Gemini n10+n20+n30 combined
- `upload-glm5-to-hf.py` — GLM-5
- `upload-kimi-to-hf.py` — Kimi K2.5

## Verification Checklist (Per Run)

1. All agents alive at end: `grep 'Agents:' moltbook-exp-JOBID_1.out | tail -1`
2. No errors in stderr: `cat moltbook-exp-JOBID_1.err`
3. Reasonable post count (expect ~30-50 posts/agent/hour for Gemini)
4. No garbage titles: run the garbage check above
5. Metadata model field is correct: `cat $SCRATCH/moltbook/results/DIR/metadata.json | jq .model`
6. Backup exists: `ls $PROJECT/moltbook/results/DIR/`
