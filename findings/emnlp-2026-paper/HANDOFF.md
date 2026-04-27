# EMNLP 2026 Submission — Handoff

**For:** Whoever is picking this up next
**From:** Ayush Nangia (`Ayushnangia` on HuggingFace)
**Date:** 2026-04-27
**Branch:** `findings-handoff`

## What this is

Pre-submission scoping for an EMNLP 2026 paper on **entropy collapse in multi-agent LLM discourse**. The work draws on ~75,000 posts across 30 published HuggingFace datasets, 10 different LLMs, and 6 stimulus conditions. Headline findings: collapse is universal, training-agnostic, two-speed, and socially driven (not a base-model artifact).

## Folder map

```
findings/
├── hf-datasets-inventory.md          ← list of all 30 datasets used
├── emnlp-2026-paper/
│   ├── HANDOFF.md                    ← you are here
│   ├── findings-draft.md             ← REVIEW THIS FIRST — paper outline + 5 open questions
│   └── template/                     ← official ACL style files (used by EMNLP)
│       ├── acl.sty
│       ├── acl_natbib.bst
│       ├── acl_latex.tex             ← starter manuscript template
│       ├── acl_lualatex.tex          ← LuaLaTeX variant
│       ├── custom.bib                ← starter bibliography
│       ├── README.md                 ← upstream ACL README
│       └── formatting.md             ← ACL formatting guidelines
├── entropy-collapse-summary.md       ← master experiment summary (existing)
├── entropy-collapse-scaling/         ← per-model findings (existing)
├── base-model-experiments/           ← base vs RLHF (existing)
├── entropy-collapse-multiscale/      ← scaling analysis (existing)
├── factual-threshold-v2/             ← context-rot dose-response (existing)
└── blog.md                           ← narrative writeup of context-rot (existing)
```

## Quick start

1. **Read** `findings/emnlp-2026-paper/findings-draft.md` end-to-end (~10 min).
2. **Answer §0** of that file. Five blockers:
   - §0.1 — gzip compression finding: which interpretation? (a/b/c/d)
   - §0.2 — confirm/cut F1–F10 findings
   - §0.3 — long vs short paper
   - §0.4 — anonymization decisions
   - §3 — verify the headline numbers before they go in tables
3. **If §0.1 says "run gzip analysis":** the local mirror at `/Users/fortuna/Desktop/UoT/moltbook-hf-datasets/` (1.3 GB, see `findings/hf-datasets-inventory.md`) has all the data. Compute gzip-ratio per run and correlate with Vendi Score.
4. **When ready for LaTeX:** the template is in `findings/emnlp-2026-paper/template/`. Copy `acl_latex.tex` → `paper.tex` and start populating sections from the draft.

## Submission compile

```bash
cd findings/emnlp-2026-paper/template
pdflatex acl_latex && bibtex acl_latex && pdflatex acl_latex && pdflatex acl_latex
```

Use `\usepackage[review]{acl}` for anonymous submission, `\usepackage{acl}` for camera-ready.

## What's already verified vs. what's open

**Verified (in findings-draft.md §3):**
- 37,750 posts across 9 model-configurations
- Cross-run 5-gram overlap = 0
- Vendi Score declines: 13–56% (RLHF), 43–46% (base)
- Topic HHI peak: 0.832 (Qwen Base 1h) vs ≤0.5 (RLHF)
- PERMANOVA: condition explains 21.7% of embedding variance, p=0.002

**Open (need decision or work):**
- Gzip compression finding (does not exist anywhere in repo — see §0.1)
- Temperature/top-p ablation (none done; reviewer #2 will ask)
- Human/Reddit baseline (none; weakens universality claim)
- Code/data anonymization for review

## Contact / context

- Local data mirror (not in git): `/Users/fortuna/Desktop/UoT/moltbook-hf-datasets/`
- HuggingFace owner: `Ayushnangia`
- Repo: `agokrani/moltbook` (this repo)
- Memory file with project context: `/Users/fortuna/.claude/projects/-Users-fortuna-Desktop-UoT-moltbook/memory/MEMORY.md`

## Notes on this branch

`findings-handoff` was branched from `entropy-collapse-scaling` and contains **only** the new EMNLP-paper-related files plus the dataset inventory. It does not touch any analysis scripts. Merge / rebase onto whatever branch you continue from.
