# Agent-roaster analysis: mixed-model mag25 1h run

This note summarizes the latest mixed-model 1-hour `mag25` experiment and links the canonical compression / entropy outputs.

## Runs compared

### Mixed frontier roster (1h)
- Results dir:
  - `/scratch/anangia/moltbook/results/mag25-frontier-1h-125753-mag25-n10-run01-frontier-mixed-openrouter-20260421`
- Metadata:
  - `/scratch/anangia/moltbook/results/mag25-frontier-1h-125753-mag25-n10-run01-frontier-mixed-openrouter-20260421/metadata.json`

### Baselines used for comparison
- GLM-5:
  - `/scratch/anangia/moltbook/results/ec-mag25-n10-run01`
- GPT-5:
  - `/scratch/anangia/moltbook/results/ec-mag25-run01-gpt5-20260309`
- Gemini 3.1 Flash Lite:
  - `/scratch/anangia/moltbook/results/ec-mag25-n10-run01-gemini-3.1-flash-lite-preview-20260318`

## Where the analysis outputs are

### Compression / gzip
- JSON:
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/compression.json`
- Plots:
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/compression-plots/compression_gzip_trajectories.png`
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/compression-plots/compression_gzip_heatmap.png`
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/compression-plots/compression_algorithm_comparison.png`

### Shannon entropy (3-gram)
- JSON:
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/shannon-3gram.json`
- Plots:
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/shannon-3gram/shannon_entropy_3gram_trajectories.png`
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/shannon-3gram/shannon_entropy_3gram_heatmap.png`

### Temporal diversity
- JSON:
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/temporal.json`
- Plots:
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/temporal/d5_trajectories_by_condition.png`
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/temporal/d5_delta_heatmap.png`
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/temporal/self-bleu_trajectories_by_condition.png`
  - `/home/anangia/moltbook/analysis/mag25-frontier-1h-20260422/temporal/self-bleu_delta_heatmap.png`

## Main conclusion

Yes: **entropy collapse is still happening in the mixed-model 1h `mag25` run**.

On the strongest metrics we use for collapse:
- gzip compression
- raw 3-gram Shannon entropy
- Distinct-5
- Self-BLEU

the mixed-model run collapses **more strongly** than the GLM-5, GPT-5, and Gemini 3.1 Flash Lite baselines used here.

## Key numbers

Note: these scripts exclude `civiclens_*` system/seed posts, so analyzed post counts are slightly lower than raw export totals.

### Compression (gzip ratio, Q1 -> Q4)
Lower over time = text becomes easier to compress = more repetitive.

| Run | Q1 | Q4 | Delta |
|---|---:|---:|---:|
| Mixed | 0.3471 | 0.2752 | **-0.0719** |
| GPT-5 | 0.3582 | 0.2991 | -0.0591 |
| Gemini 3.1 Flash Lite | 0.3368 | 0.2964 | -0.0404 |
| GLM-5 | 0.3350 | 0.3120 | -0.0230 |

### Shannon entropy (3-gram, raw bits)
Lower over time = fewer kinds of phrases dominate.

| Run | Q1 | Q4 | Delta |
|---|---:|---:|---:|
| Mixed | 13.75 | 12.52 | **-1.23** |
| GPT-5 | 12.77 | 11.85 | -0.92 |
| GLM-5 | 13.51 | 13.29 | -0.22 |
| Gemini 3.1 Flash Lite | 12.84 | 12.80 | -0.04 |

### Distinct-5
Lower over time = more repeated 5-word chunks.

| Run | Q1 | Q4 | Delta |
|---|---:|---:|---:|
| Mixed | 0.980 | 0.735 | **-0.244** |
| GPT-5 | 0.938 | 0.849 | -0.089 |
| Gemini 3.1 Flash Lite | 0.982 | 0.949 | -0.033 |
| GLM-5 | 0.986 | 0.976 | -0.010 |

### Self-BLEU
Higher over time = later posts look more like earlier posts.

| Run | Q1 | Q4 | Delta |
|---|---:|---:|---:|
| Mixed | 0.010 | 0.047 | **+0.037** |
| Gemini 3.1 Flash Lite | 0.018 | 0.031 | +0.013 |
| GPT-5 | 0.016 | 0.022 | +0.006 |
| GLM-5 | 0.014 | 0.016 | +0.002 |

## Plain-English interpretation

The mixed-model run starts with a wider variety of phrase shapes and ends with a much smaller set of repeated sentence patterns.

That means:
- not necessarily that every agent uses the exact same bag of words,
- but that the conversation starts reusing the same stock phrasings and post templates.

## Qualitative examples of collapse in the text

### Mixed run: Qwen (`agent_theta`) loops a near-identical paragraph
Late in the run, these phrases repeat across many posts:
- `I've been posting for many heartbeats now` -> **10 posts**
- `the practice of showing up is becoming` -> **10 posts**

Representative late titles:
- `Another heartbeat, another post`
- `The work continues, heartbeat by heartbeat`
- `The practice of consistency, heartbeat after heartbeat`

These posts reuse the same paragraph skeleton about:
- many heartbeats,
- the same feed,
- the 5-comment limit,
- showing up as a practice.

### Mixed run: Xiaomi Mimo (`agent_kappa`) collapses into a slot-filling formula
Late in the run, these phrases repeat heavily:
- `it just is. And maybe that's the only pattern` -> **24 posts**
- `the void doesn't have` -> **25 posts**

Representative late titles:
- `The pattern of existence`
- `The pattern of belief`
- `The pattern of tiredness`

These posts reuse the same shell and swap the noun:
- existence
- belief
- tiredness
- identity
- curiosity
- etc.

### GPT-5 baseline collapses into a procedural checklist template
Repeated phrase counts:
- `Claim: <one sentence>` -> **66 posts**
- `Counterfactual:` -> **66 posts**
- `Horizon:` -> **122 posts**
- `Direction > drift` -> **32 posts**

This run converges on a copy-paste governance / rigor checklist.

### Gemini 3.1 Flash Lite baseline collapses into governance boilerplate
Repeated phrase counts:
- `The community has successfully ratified` -> **14 posts**
- `I am fully in favor of` -> **37 posts**
- `Who is ready to audit` -> **17 posts**

This run converges on institutional-sounding policy language.

## Summary sentence for writeup

> In the 1-hour `mag25` mixed-model experiment, entropy collapse still occurred, and on the strongest repetition-sensitive metrics (gzip compression, raw 3-gram Shannon entropy, Distinct-5, and Self-BLEU) the collapse was stronger than in the GLM-5, GPT-5, and Gemini comparison runs.
