# Canonical gzip compression findings — resumed/merged version

This re-runs the canonical 48-run gzip analysis (`scripts/gzip/compute_compression.py`)
**after** merging in the 8 resumed runs that were prematurely terminated in the
original exports (Gemini Flash Lite provider dropouts + GPT-5 wall-clock cutoff).

## What changed vs `findings/entropy-collapse-gzip/`

In the previous run, 8 of the 48 canonical experiments had effectively **empty
Q3 and/or Q4 bins** — their agent populations had dropped to zero before the
hour was up:

| Run | Old Q1–Q4 post counts | New Q1–Q4 post counts |
|---|---|---|
| GPT-5/n10/mag0/ec-mag0-run04 | 114 / 126 / 129 / **0** | 114 / 126 / 144 / 96 |
| GPT-5/n10/mag1/ec-mag1-run04 | 134 / 143 / 127 / **0** | 134 / 143 / 135 / 96 |
| Gemini/n10/dom-agi/ec-dom-agi-n10-run01 | 103 / 42 / **0** / **0** | 103 / 97 / 139 / 57 |
| Gemini/n10/dom-tech/ec-dom-tech-n10-run01 | 107 / 85 / 11 / **0** | 107 / 85 / 57 / 82 |
| Gemini/n20/dom-agi/ec-dom-agi-n20-run01 | 241 / 159 / **0** / **0** | 241 / 178 / 83 / 141 |
| Gemini/n20/mag5/ec-mag5-n20-run01 | 231 / 174 / **0** / **0** | 231 / 240 / 272 / 112 |
| Gemini/n30/mag25/ec-mag25-n30-run01 | 293 / 292 / **0** / **0** | 294 / 319 / 291 / 374 |
| Gemini/n30/mag5/ec-mag5-n30-run01 | 306 / 291 / **0** / **0** | 306 / 342 / 395 / 375 |

Empty bins compress to a tiny fixed-string size, which made gzip ratios in those
bins drop to ~0.0 and inflated the apparent Q1→Q4 delta. The merged data
(re-timestamped via `scripts/retimestamp/retimestamp_resumed.py` so the
inter-segment pause collapses to a 1-second gap) gives full Q1–Q4 coverage for
all 48 runs. The four runs whose merged span exceeds 60 min (61–63 min) are
naturally trimmed by the existing first-60-minute filter inside
`compute_compression.py` (`elapsed > 60: continue`).

## Headline result

| Algorithm | Old mean Δ | New mean Δ | Old declines | New declines | Old rel. drop | New rel. drop |
|---|---:|---:|---:|---:|---:|---:|
| gzip  | -0.0889 | **-0.0366** | 46/48 | 44/48 | -27.3% | -11.4% |
| bzip2 | -0.0627 | **-0.0167** | 38/48 | 35/48 | -22.8% | -6.3% |
| zlib  | -0.0892 | **-0.0369** | 46/48 | 44/48 | -27.3% | -11.5% |

**Roughly half of the previously-reported gzip "entropy collapse" was an
artifact** of the 8 prematurely-terminated runs whose Q4 was empty. The real
effect is still negative and statistically present — Q1→Q4 compression ratio
declines in 44/48 runs — but the average drop is ~3.7% absolute, not ~9%.

Two new sign-flips emerged in the merged runs (ratios actually *increased* from
Q1 to Q4):

- Gemini/n20/dom-agi/ec-dom-agi-n20-run01 → Δ = +0.042
- Gemini/n20/mag5/ec-mag5-n20-run01 → Δ = +0.019

Combined with the previously-known Gemini/n20/mag0 (Δ = +0.014) and
GPT-5/n10/mag25 (Δ = +0.079), this pushes the count of non-declining runs from
2 → 4 (out of 48).

## Per-set means (gzip)

| Set | n | Mean Δgzip |
|---|---:|---:|
| GPT-5   | 18 | -0.0415 |
| Gemini  | 18 | -0.0433 |
| Kimi    | 6  | -0.0268 |
| GLM-5   | 6  | -0.0114 |

GLM-5 shows the smallest decline; it also has the shortest sessions
(228–317 posts/run) so this may be statistical-power limited.

## Inventory

| Quantity | Value |
|---|---:|
| Canonical runs | 48 |
| Resumed+merged overrides applied | 8 |
| Agent-authored posts in first 60 min | 35,725 |
| Agent-authored posts excluded after 60 min | 2,765 |

The 8 overridden runs are read from `data/canonical-merged/<run>/posts.jsonl`
(produced by `scripts/retimestamp/retimestamp_resumed.py` on
2026-05-03). The other 40 are read from their original canonical paths
unchanged.

## How to reproduce

```bash
# 1. (Re-)download the resumes dataset
python3 -c "from huggingface_hub import snapshot_download; \
            snapshot_download(repo_id='Ayushnangia/moltbook-entropy-collapse-resumes', \
                              repo_type='dataset', local_dir='data/resumed')"

# 2. Merge + retimestamp
python3 scripts/retimestamp/retimestamp_resumed.py    # → data/canonical-merged/

# 3. Run gzip with the merge overlaid on the canonical inventory
python3 scripts/gzip/compute_compression.py \
  --data-root data \
  --merged-overrides-dir data/canonical-merged \
  --output findings/entropy-collapse-gzip/results-canonical-48-resumed.json

# 4. Plot
python3 scripts/gzip/plot_compression.py \
  --input findings/entropy-collapse-gzip/results-canonical-48-resumed.json \
  --output-dir findings/entropy-collapse-gzip-resumed
```

Outputs in this directory:

- `compression_gzip_trajectories.png` — six-condition trajectories
- `compression_gzip_heatmap.png` — Δ heatmap per (set/scale, condition)
- `compression_algorithm_comparison.png` — gzip / bzip2 / zlib side-by-side
- `summary.json` — aggregate stats and the 4 non-declining runs

The raw per-run results are at
`../entropy-collapse-gzip/results-canonical-48-resumed.json`.
