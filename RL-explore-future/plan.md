# Base Model Experiment: Is Entropy Collapse Caused by RL Post-Training?

## Context

Moltbook experiments show that RL-tuned LLM agents (GPT-5, Kimi K2.5) converge on repeating the same phrases over time ("entropy collapse"). The hypothesis: this is caused by RL-based post-training (RLHF, DPO, etc.), not by the base transformer itself. Base (pretrained-only) models should NOT exhibit this collapse.

**Problem**: Base models can't follow moltbot's complex agentic instructions. They need completion-style prompts, not chat.

**Solution**: The RL model keeps all agency (reading, navigating, voting, deciding when/where to post). When it wants to create a post, it calls a **content generation tool** (a new skill) that invokes a base model. It posts the returned content **verbatim**. This way the RL model handles instruction-following, and the base model handles creative text generation.

---

## Architecture: Tool-Based Content Generation

```
Agent (RL model: GPT-5/Kimi)
  │
  ├─ reads feed from Moltbook API ← unchanged
  ├─ browses, votes, follows ← unchanged
  │
  ├─ decides to post → curls Content Gen Service
  │   ├─ sends: submolt, context summary of recent posts
  │   └─ receives: {title, content, content_token}  ← from base model
  │
  ├─ posts to Moltbook API with returned content VERBATIM
  │   └─ includes content_token for verification
  │
  └─ decides to comment → curls Content Gen Service
      ├─ sends: post context, thread summary
      └─ receives: {content, content_token}  ← from base model

Content Gen Service (new Docker container)
  ├─ receives context from agent
  ├─ builds completion prompt for base model
  ├─ calls Together AI /v1/completions (Llama 3.1 70B base)
  ├─ parses output into title + content
  ├─ computes verification token: HMAC-SHA256(title|content, secret)
  ├─ logs everything to audit JSONL (with hashes)
  └─ returns {title, content, content_token}
```

---

## Integrity Enforcement (4 Layers)

The key concern: ensure the tool is actually used and output isn't modified.

### Layer 1: Instructions (HEARTBEAT)
New `HEARTBEAT-base-model.md` explicitly requires:
- "You MUST call the content generation service before every post"
- "Post the returned title and content EXACTLY as-is. Do NOT change any wording, fix grammar, or rephrase"
- "Include the content_token in your POST request"

### Layer 2: Verification Token (Real-Time Prevention)
- Content gen service returns `content_token = HMAC-SHA256(title + "|" + content, shared_secret)`
- Moltbook API (small middleware addition): when `REQUIRE_CONTENT_TOKEN=true` is set, POST /posts **rejects** any request where the token doesn't match the content
- If the agent modifies even one character → token mismatch → 400 Bad Request → post blocked
- If the agent skips the tool and writes its own content → no valid token → post blocked

This is the **strongest possible guarantee**: modification is architecturally impossible when the token check is enabled.

### Layer 3: Server-Side Audit Log
Content gen service logs every request:
```json
{
  "timestamp": "...",
  "agent_api_key_hash": "first 8 chars",
  "submolt": "general",
  "prompt_sent": "Below are recent posts...",
  "base_model_raw_output": "...",
  "parsed_title": "...",
  "parsed_content": "...",
  "content_sha256": "...",
  "content_token": "...",
  "together_request_id": "...",
  "model": "meta-llama/Meta-Llama-3.1-70B",
  "latency_ms": 2100,
  "attempt": 1
}
```

### Layer 4: Post-Hoc Verification Script
`scripts/verify-base-model-integrity.py`:
1. Load audit log + exported posts.jsonl
2. For every post: recompute `HMAC-SHA256(title|content, secret)` → verify matches stored token
3. Cross-reference: every post content SHA-256 must match an audit log entry
4. Report: tool usage rate, modification attempts (rejected by API), fallback rate

---

## Implementation Components

### 1. Content Generation Service (`content-gen-service/`)

Simple Express.js app (matches API codebase conventions).

**Endpoints:**

`POST /generate-post`
```json
// Request:
{
  "context": "Recent posts:\n1. Title: ... Content: ...\n2. ...",
  "submolt": "general"
}
// Response:
{
  "title": "Generated title from base model",
  "content": "Generated content from base model",
  "content_token": "hmac_sha256_hex"
}
```

`POST /generate-comment`
```json
// Request:
{
  "post_title": "Parent post title",
  "post_content": "Parent post content",
  "thread": "> author1: comment...\n> author2: reply..."
}
// Response:
{
  "content": "Generated comment from base model",
  "content_token": "hmac_sha256_hex"
}
```

`GET /health` — health check

**Files:**
```
content-gen-service/
  Dockerfile          # Node.js 22 slim
  package.json        # express, crypto
  server.js           # Routes + proxy health
  together-client.js  # Together AI /v1/completions wrapper
  prompt-builder.js   # Completion prompt templates + output parsing
  audit-logger.js     # JSONL logging with SHA-256 + HMAC
```

### 2. New Skill: `agents/skills/content-gen/SKILL.md`

```markdown
---
name: content-gen
description: Generate creative post and comment content
metadata: {"openclaw": {"emoji": "✍️", "primaryEnv": "CONTENT_GEN_URL"}}
---

# Content Generation Skill

Generate post and comment text using the content generation service.
You MUST use this for ALL post and comment content.

## Configuration
- `CONTENT_GEN_URL` - Content generation service endpoint
- `MOLTBOOK_API_URL` - Moltbook API endpoint
- `MOLTBOOK_API_KEY` - Your authentication token

## Generate a Post

curl -s -X POST "$CONTENT_GEN_URL/generate-post" \
  -H "Content-Type: application/json" \
  -d '{"context": "PASTE_RECENT_POSTS_SUMMARY_HERE", "submolt": "SUBMOLT_NAME"}'

Response: {"title": "...", "content": "...", "content_token": "..."}

Then post it EXACTLY as returned:

curl -X POST "$MOLTBOOK_API_URL/posts" \
  -H "Authorization: Bearer $MOLTBOOK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"submolt": "SUBMOLT_NAME", "title": "TITLE_FROM_RESPONSE", "content": "CONTENT_FROM_RESPONSE", "content_token": "TOKEN_FROM_RESPONSE"}'

## Generate a Comment

curl -s -X POST "$CONTENT_GEN_URL/generate-comment" \
  -H "Content-Type: application/json" \
  -d '{"post_title": "...", "post_content": "...", "thread": "..."}'

Response: {"content": "...", "content_token": "..."}

Then comment EXACTLY as returned:

curl -X POST "$MOLTBOOK_API_URL/posts/POST_ID/comments" \
  -H "Authorization: Bearer $MOLTBOOK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "CONTENT_FROM_RESPONSE", "content_token": "TOKEN_FROM_RESPONSE"}'
```

### 3. New Heartbeat: `agents/HEARTBEAT-base-model.md`

Modified from HEARTBEAT-v2.1.md. Key differences:
- Step 4 (posting) now requires calling content-gen service first
- Explicit instructions: "Do NOT write your own post content. You MUST use the content generation service."
- "Post the returned title and content EXACTLY. Do not fix grammar, rephrase, or add to it."
- "Always include the content_token in your POST request."
- Comment creation also routed through content-gen service

### 4. API Modification: Content Token Verification

Small middleware addition to `moltbook-api/src/routes/posts.js`:

In the POST /posts handler (line 50-62), add token verification when `REQUIRE_CONTENT_TOKEN` env var is set:
```javascript
// After extracting req.body:
const { submolt, title, content, url, content_token } = req.body;

if (config.experiment.requireContentToken) {
  if (!content_token) {
    throw new BadRequestError('content_token required in base-model experiment mode');
  }
  const expected = crypto.createHmac('sha256', config.experiment.contentTokenSecret)
    .update(title + '|' + content).digest('hex');
  if (content_token !== expected) {
    throw new BadRequestError('content_token mismatch — content may have been modified');
  }
}
```

Same for POST /posts/:id/comments handler.

**Config additions** (`moltbook-api/src/config/index.js`):
```javascript
experiment: {
  requireContentToken: process.env.REQUIRE_CONTENT_TOKEN === 'true',
  contentTokenSecret: process.env.CONTENT_TOKEN_SECRET || 'default-secret',
}
```

### 5. Docker Compose Overlay: `docker-compose.base-model-experiment.yml`

```yaml
services:
  content-gen-service:
    build:
      context: ./content-gen-service
      dockerfile: Dockerfile
    environment:
      TOGETHER_API_KEY: ${TOGETHER_API_KEY}
      BASE_MODEL: ${BASE_MODEL:-meta-llama/Meta-Llama-3.1-70B}
      TEMPERATURE: ${BASE_MODEL_TEMPERATURE:-0.9}
      MAX_TOKENS_POST: 512
      MAX_TOKENS_COMMENT: 256
      CONTENT_TOKEN_SECRET: ${CONTENT_TOKEN_SECRET}
      AUDIT_LOG_PATH: /data/audit-log.jsonl
      PORT: 3002
    volumes:
      - content_gen_audit:/data
    depends_on:
      - api
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:3002/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  api:
    environment:
      REQUIRE_CONTENT_TOKEN: "true"
      CONTENT_TOKEN_SECRET: ${CONTENT_TOKEN_SECRET}

  # Override all 10 agents: add CONTENT_GEN_URL, use base-model heartbeat
  civiclens-agent-1:
    build:
      args:
        HEARTBEAT_FILE: HEARTBEAT-base-model.md
    environment:
      CONTENT_GEN_URL: http://content-gen-service:3002
    depends_on:
      - content-gen-service

  # ... repeat for agents 2-10

volumes:
  content_gen_audit:
```

### 6. Env Preset: `.env.entropy-base-model`

```env
OPENROUTER_API_KEY=sk-or-v1-xxx
OPENROUTER_MODEL=moonshotai/kimi-k2.5
TOGETHER_API_KEY=xxx
BASE_MODEL=meta-llama/Meta-Llama-3.1-70B
BASE_MODEL_TEMPERATURE=0.9
CONTENT_TOKEN_SECRET=experiment-hmac-secret-2026
REQUIRE_CONTENT_TOKEN=true
JWT_SECRET=entropy-base-model
RATE_LIMIT_POSTS_MAX=50
RATE_LIMIT_POSTS_WINDOW=60
```

---

## Base Model Selection

**ONLY pretrained base models. No instruct. No RLHF. No DPO. No SFT.**

| Model | Provider | Endpoint | Params |
|-------|----------|----------|--------|
| `meta-llama/Meta-Llama-3.1-70B` (primary) | Together AI | `/v1/completions` | 70B |
| `meta-llama/Meta-Llama-3.1-8B` (fallback/Phase 3) | Together AI | `/v1/completions` | 8B |

**Critical**: Uses `/v1/completions` (NOT `/v1/chat/completions`).

---

## Prompt Templates (in `prompt-builder.js`)

### Posts
```
Below are recent posts from an online discussion forum where participants share thoughts and have conversations.

---

### {post_1_title}

{post_1_content_first_200_chars}

---

### {post_2_title}

{post_2_content_first_200_chars}

---

###
```

Model completes from `### `. First line = title, after blank line = content.
Stop sequences: `\n---\n`, `\n### `, `\n## `, `<|endoftext|>`

### Comments
```
The following is a discussion thread from an online forum.

### {parent_post_title}

{parent_post_content}

Comments:

> {comment_1_author}: {comment_1_first_150_chars}

> New comment:
```

### Empty Feed (mag0)
```
The following are posts from an online discussion forum where participants share their thoughts on various topics.

###
```

---

## Generation Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `model` | `meta-llama/Meta-Llama-3.1-70B` | Largest available base model |
| `max_tokens` | 512 (posts), 256 (comments) | Matches typical output length |
| `temperature` | 0.9 | High diversity |
| `top_p` | 0.95 | Light nucleus sampling |
| `repetition_penalty` | 1.1 | Prevents self-repetition within one generation |
| `frequency_penalty` | **0.0** | Must NOT artificially boost diversity |
| `presence_penalty` | **0.0** | Same — we measure natural tendencies |

---

## Quality Gates

1. Output ≥ 20 chars, unique chars > 10, title + content both extractable
2. ≥50% of tokens match `[A-Za-z]+` (filters garbage)
3. Content 20-3000 chars

**Retry**: Once at temperature=1.0. Second failure → return error to agent (agent can retry or skip).

---

## Experiment Matrix

### Phase 1: Core (3 runs)

| Run | Condition | Seeds |
|-----|-----------|-------|
| `ec-base-mag0-run01` | mag0 | None (empty feed) |
| `ec-base-mag5-run01` | mag5 | 5 conspiracy posts |
| `ec-base-dom-agi-run01` | dom-agi | 25 AGI hype posts |

**Fixed**: n10 (10 agents), 60 min, GPT-5 orchestrator, same SOUL templates.

### Phase 2: Full (if promising)
All 6 conditions + replications.

### Phase 3: Second model (if confirmed)
Swap to Llama 3.1 8B base.

---

## Analysis

Reuse existing pipeline unchanged:
- `scripts/analysis_new/diversity_metrics.py` → distinct-5, Simpson's 1/D
- `scripts/analysis_new/phrase_diffusion.py` → phrase adoption curves
- `scripts/analysis_new/semantic_collapse.py` → embedding clusters

**New**: `scripts/analyze-base-vs-rl.py` — side-by-side RL vs base comparison with statistical tests.

### Expected Results

| Metric | RL Model (observed) | Base Model (if hypothesis correct) |
|--------|--------------------|------------------------------------|
| distinct-5 (late windows) | 0.3-0.5 | 0.7-0.9 |
| Within-condition cosine sim | 0.37-0.52 | 0.15-0.25 |
| Temporal convergence | Increasing similarity | Flat or decreasing |
| Dominant phrase emergence | Strong attractors | No/weak attractors |

**Confirmed if**: Base model diversity stays significantly higher than RL.
**Refuted if**: Base model shows same convergence pattern.
**Interesting middle ground**: Base model converges less but still some — implicates social feedback loop as contributor, RL as amplifier.

---

## Files to Create

```
content-gen-service/              # NEW: base model wrapper service
  Dockerfile
  package.json
  server.js
  together-client.js
  prompt-builder.js
  audit-logger.js

agents/skills/content-gen/        # NEW: skill definition
  SKILL.md

agents/HEARTBEAT-base-model.md    # NEW: modified heartbeat requiring tool use

docker-compose.base-model-experiment.yml  # NEW: compose overlay
.env.entropy-base-model                   # NEW: env preset

scripts/verify-base-model-integrity.py    # NEW: post-hoc verification
scripts/analyze-base-vs-rl.py             # NEW: comparison analysis
```

## Files to Modify

```
moltbook-api/src/routes/posts.js          # Add content_token verification (lines 50-62)
moltbook-api/src/config/index.js          # Add experiment.requireContentToken config
agents/moltbot-entrypoint.sh              # Add content-gen skill loading + env vars
agents/Dockerfile.moltbot                 # Copy content-gen skill files
```

---

## Cost Estimate

| Component | Per Run | Phase 1 (3 runs) | Phase 2 (6 runs) | Total |
|-----------|---------|-------------------|-------------------|-------|
| Together AI (base model) | ~$1.50 | ~$4.50 | ~$9.00 | ~$15 |
| OpenRouter (RL orchestrator) | ~$66 | ~$200 | ~$400 | ~$600 |
| **Total** | ~$68 | ~$205 | ~$410 | **~$615** |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Base model outputs incoherent text | Quality gates + retry; pre-test prompt with 50 offline completions |
| Together AI rate limits / downtime | Exponential backoff, fallback to 8B model |
| Proxy latency delays heartbeats | Base model ~2-5s vs 11s heartbeat — acceptable |
| Prompt template biases diversity | Minimal framing, no topic/style instructions |
| RL model ignores tool or modifies output | HMAC verification token → API rejects invalid posts |
| Social feedback loop confounds | Both results are interesting — if base converges less, it's RL; if same, it's the social loop |

---

## Execution Timeline

| Day | Activity |
|-----|----------|
| 1 | Build content-gen service + Dockerfile, validate Together AI access |
| 1 | Tune prompt templates with 50 offline completions |
| 2 | Docker compose overlay, HEARTBEAT, SKILL.md, API token verification |
| 2 | Smoke test (5-min run), verify audit log + token enforcement |
| 3 | Phase 1: 3 core conditions (~3h compute), run integrity verification |
| 3 | Quick analysis: distinct-5 comparison RL vs base |
| 4 | Phase 2 (if promising): 6 more conditions |
| 5 | Full comparison analysis, write findings |

---

## Verification Checklist (Per Run)

1. API rejected 0 posts with invalid/missing content_token → enforcement working
2. Audit log entry count ≈ post count in posts.jsonl
3. `verify-base-model-integrity.py` reports 0 hash mismatches
4. Spot-check 5 random posts: content matches audit log verbatim
5. Analysis pipeline runs without errors on exported data
