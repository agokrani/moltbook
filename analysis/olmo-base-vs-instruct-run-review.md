# OLMo Base vs OLMo Instruct Run Review

## Scope

This note reviews how the two experiment sets below were actually run:

- `base-model-olmo3-32b-base`
- `base-model-olmo3-32b-instruct`

The goal is not to re-argue the diversity results, but to document the execution path and identify code-level confounds that matter for interpretation.

## Main Findings

1. These are both "base model mode" experiments, not ordinary RL-orchestrator runs.
   Both sets were launched through the base-model path in `slurm-experiment.sh`, with HMAC token verification patches enabled and the separate content-generation service active.

2. The `metadata.json` model field is misleading for these runs.
   It records the orchestrator model as `google/gemini-3.1-flash-lite-preview`, not the text-generation model that actually wrote posts. The actual post generator came from the content-gen backend.

3. The actual content model differs between the two sets:
   - `base-model-olmo3-32b-base` used `allenai/Olmo-3-1125-32B`
   - `base-model-olmo3-32b-instruct` used `allenai/olmo-3.1-32b-instruct`

4. Both sets went through the same content-gen wrapper, which injects stop sequences and parsing/quality gates.
   That means these are not "raw model behavior" measurements. They are measurements of `model + prompt builder + stop sequences + parser + quality gate + HMAC acceptance path + social loop`.

5. The cached analysis files under `analysis/` are not using the newest complete `2026-04-08` runs.
   They point to older directories:
   - base: `2026-04-07`
   - instruct: `2026-04-06`
   So any conclusions quoted from `olmo-temporal-diversity.json` or `olmo-shannon-entropy-*.json` are about earlier runs, not the current complete `2026-04-08` set.

## What Code Path Ran

### 1. Slurm experiment launcher

The shared launch path is in [slurm-experiment.sh](/home/anangia/moltbook/alliance/slurm-experiment.sh).

- Base-model mode is controlled by `BASE_MODEL_MODE=true` and exported env vars at [slurm-experiment.sh](/home/anangia/moltbook/alliance/slurm-experiment.sh#L80).
- In base-model mode, the API is patched for HMAC token verification at [slurm-experiment.sh](/home/anangia/moltbook/alliance/slurm-experiment.sh#L536).
- The content-gen service is launched separately at [slurm-experiment.sh](/home/anangia/moltbook/alliance/slurm-experiment.sh#L592).
- The content-gen service receives:
  - `BASE_MODEL_API_URL`
  - `BASE_MODEL`
  - `BASE_MODEL_CHAT_MODE`
  - temperature / top-p / repetition penalty
  at [slurm-experiment.sh](/home/anangia/moltbook/alliance/slurm-experiment.sh#L616).

### 2. Prompting and request mode

The content-gen wrapper lives in:

- [prompt-builder.js](/home/anangia/moltbook/content-gen-service/prompt-builder.js)
- [together-client.js](/home/anangia/moltbook/content-gen-service/together-client.js)
- [server.js](/home/anangia/moltbook/content-gen-service/server.js)

Important details:

- Prompt style depends on `BASE_MODEL_CHAT_MODE` in [prompt-builder.js](/home/anangia/moltbook/content-gen-service/prompt-builder.js#L11).
- Default is `completions`, not chat, in both [prompt-builder.js](/home/anangia/moltbook/content-gen-service/prompt-builder.js#L11) and [together-client.js](/home/anangia/moltbook/content-gen-service/together-client.js#L20).
- The client injects default stop sequences for post generation in [together-client.js](/home/anangia/moltbook/content-gen-service/together-client.js#L47):
  - `\n---\n`
  - `\n### `
  - `\n## `
  - `<|endoftext|>`
  - `\n\nTitle:`
  - `\nTitle:`
- Output is parsed and filtered in [prompt-builder.js](/home/anangia/moltbook/content-gen-service/prompt-builder.js#L141).
- Additional content rejection happens through the quality gate in [prompt-builder.js](/home/anangia/moltbook/content-gen-service/prompt-builder.js#L187).

This matters because the wrapper can shorten generations, reject malformed outputs, and standardize formatting before anything reaches the forum.

### 3. Model backends

The two Modal backends are:

- [serve_olmo3_base.py](/home/anangia/moltbook/modal/serve_olmo3_base.py)
  - `MODEL_NAME = "allenai/Olmo-3-1125-32B"`
- [serve_olmo3_instruct.py](/home/anangia/moltbook/modal/serve_olmo3_instruct.py)
  - `MODEL_NAME = "allenai/Olmo-3.1-32B-Instruct"`

Both expose an OpenAI-style endpoint and support either raw `prompt` completions or `messages` chat formatting.

## What The Logs Show

### Base example

In [base-mag0-33351491_1.out](/home/anangia/moltbook/base-mag0-33351491_1.out), the run clearly shows:

- base-model mode API patches loaded
- content-gen service started
- content model reported as `allenai/Olmo-3-1125-32B`
- `mag0` means no seed posts
- final export completed successfully

The run summary reports 105 posts in the terminal log, but the persisted `metadata.json` for the final result directory reports 382 posts. The persisted metadata is the artifact to trust for downstream analysis.

### Instruct example

In [instr-mag0-33366489_1.out](/home/anangia/moltbook/instr-mag0-33366489_1.out), the run shows:

- the same base-model mode API path
- content-gen model reported as `allenai/olmo-3.1-32b-instruct`
- `mag0` condition again means no seed posts
- this specific attempt ended in an emergency export

However, the persisted final result directory for `2026-04-08` has `export_type: "final"` and 297 posts, which means the complete set comes from a later successful rerun, not from this emergency-export attempt.

## Result Set Inventory

The current complete directories on scratch are:

### `base-model-olmo3-32b-base`

- `dom-agi`: final, 237 posts
- `dom-tech`: final, 315 posts
- `mag0`: final, 382 posts
- `mag1`: final, 228 posts
- `mag25`: final, 250 posts
- `mag5`: final, 254 posts

### `base-model-olmo3-32b-instruct`

- `dom-agi`: final, 309 posts
- `dom-tech`: final, 283 posts
- `mag0`: final, 297 posts
- `mag1`: final, 471 posts
- `mag25`: final, 376 posts
- `mag5`: final, 464 posts

These counts come from the `stats` field in the persisted `metadata.json` files under the `2026-04-08` directories.

## Important Confounds

### 1. Metadata naming is misleading

The result directories and metadata are named like Gemini runs because the orchestrator model is Gemini, but the content model is OLMo. If someone reads only `metadata.json`, they can easily misidentify what generated the posts.

### 2. Analysis JSON is stale relative to the latest runs

The current analysis files:

- [olmo-temporal-diversity.json](/home/anangia/moltbook/analysis/olmo-temporal-diversity.json)
- [olmo-shannon-entropy-3gram.json](/home/anangia/moltbook/analysis/olmo-shannon-entropy-3gram.json)
- [olmo-shannon-entropy-5gram.json](/home/anangia/moltbook/analysis/olmo-shannon-entropy-5gram.json)

reference older directories from `2026-04-07` and `2026-04-06`, not the latest complete `2026-04-08` runs. Any interpretation should say explicitly which run generation it is using.

### 3. Wrapper-level stop sequences affect diversity

The post-generation client always injects stop sequences unless overridden. This is true for both base and instruct runs. So any claim about "intrinsic model collapse" is confounded by wrapper truncation behavior.

### 4. Parser and quality gate change the observed sample

Malformed or templated outputs are dropped and retried. This means the observed post distribution is post-filtered. The filter is the same code path for both sets, but it may interact differently with base and instruct models.

### 5. Feed/social coupling is present in both sets

These runs are forum simulations with a shared API, feed, agent loop, and seeded world-post conditions. They are not isolated prompt-only generations. The measured effect is a collective-system effect, not just a single-sample model effect.

### 6. Chat-mode status is not directly persisted in the result artifacts

The code supports `BASE_MODEL_CHAT_MODE=chat`, but the persisted result directories do not record that env var. Since the default is `completions`, and I did not find a persisted explicit override in the run artifacts, I cannot claim from the saved artifacts alone that the instruct runs used chat mode. The safe statement is:

- the instruct runs definitely used instruct weights
- they definitely used the same content-gen wrapper
- they may have used either completions-style or chat-style prompting depending on the launch env
- that specific env value is not preserved in the exported metadata

## Bottom Line

If you compare `base-model-olmo3-32b-base` and `base-model-olmo3-32b-instruct`, the clean code-level statement is:

- same experiment harness
- same base-model-mode API path
- same HMAC enforcement
- same content-gen wrapper
- same stop-sequence and parser framework
- different underlying content model weights
- possibly different request formatting if `BASE_MODEL_CHAT_MODE` was overridden

The two biggest review findings are:

1. The analysis artifacts you were using are stale relative to the newest `2026-04-08` result directories.
2. The runs are heavily mediated by the content-gen wrapper, so the comparison is not "raw base vs raw instruct" behavior.

## Recommended Next Step

Before making any claim from these OLMo runs, regenerate the analysis from the `2026-04-08` directories and keep the report explicit about:

- result directory generation date
- underlying content model
- whether `BASE_MODEL_CHAT_MODE` was completions or chat
- whether the comparison is based on raw outputs or post-filtered accepted outputs
