# EMNLP 2026 Submission — Findings Draft for Review

**Status:** Pre-submission scoping document. Review and confirm before LaTeX conversion.
**Working title (placeholder):** *Entropy Collapse in Multi-Agent LLM Discourse: A Universal, Training-Agnostic Phenomenon*
**Target venue:** EMNLP 2026 (long paper, main conference; alternative: Findings)
**Author:** Ayush Nangia

---

## 0. ⚠️ Things You Need to Decide / Clarify First

Before I write the LaTeX, I need your input on these. Please answer or annotate inline.

### 0.1 The "gzip compression" finding — I cannot find it

You mentioned **gzip compression** as one of the surprising findings. I did an exhaustive search across:
- All branches in `moltbook/` (including remotes)
- All `findings/`, `scripts/`, `experiments/`, `docs/`
- The git log (commit messages)
- The git stash
- Sibling dirs (`Sandbox/dataclean`, `slides_moltbook`, `CCDB`)

**Zero hits.** All matches were in `node_modules/` or `.dist-info/RECORD` files for unrelated libraries. There is no analysis script, no plot, no writeup that computes gzip-based compression as a metric.

**Possible interpretations — please pick one:**

- [ ] **(a) It's a planned/aspirational analysis.** I should run it now: compute gzip-compressibility of each run's concatenated post text as a proxy for entropy, and add it as a new finding with its own section. This is a known technique (Kolmogorov-style compression entropy; Jiang et al. 2023's "low-resource gzip text classification" popularized it for NLP).
- [ ] **(b) It exists somewhere I missed.** Point me to the path/branch/repo and I'll incorporate it.
- [ ] **(c) You meant something different.** What's the actual finding? (e.g., compression as a topic-clustering signal; ratio of unique-bytes-to-total as a diversity proxy.)
- [ ] **(d) Drop it from this submission.** Stick to what's already in `findings/`.

**My recommendation: (a).** It would be a strong methodological add — gzip-ratio vs Vendi Score correlation across all 30 datasets would tell us "is the fancy embedding-based diversity metric we're using necessary, or does naive compression detect the same collapse?" Either answer is publishable.

### 0.2 Other surprising findings — confirm or add

I extracted these from `findings/entropy-collapse-summary.md`, the per-model `findings.md` files, `entropy-collapse-multiscale/findings.md`, and `blog.md`. Tick the ones you want in the paper, cross out anything that's wrong, and add anything I missed.

| # | Finding | In paper? | Notes |
|---|---|---|---|
| F1 | Entropy collapse is **universal across models** (GPT-5, Gemini, GLM-5, Kimi-K2.5) and across training regimes (base vs RLHF) | ☐ | Headline result. n=37,750 posts, 9 model-configs, 0 exceptions. |
| F2 | **Phrase collapse is fast (minutes), topic collapse is slow (~1 hour)** — two-speed convergence | ☐ | Strong mechanism finding. |
| F3 | **Cross-run 5-gram overlap is exactly 0** — every run discovers a *unique* attractor | ☐ | Most-mentioned-as-surprising in your summaries. |
| F4 | **RLHF is a partial brake, not a cure** — base models collapse harder (HHI 0.832 vs ≤0.5 for RLHF) but the *character* differs (looping nonsense vs generic helpfulness) | ☐ | Novel claim; clean A/B (Qwen base vs instruct, same architecture). |
| F5 | **Convergence is social, not intrinsic** — first-post vs late-window structural similarity rises 39% (n30); base-model prior rejected by bootstrap CI | ☐ | Strongest *causal* claim you have. PERMANOVA p=0.002. |
| F6 | **More agents → more collapse** (distinct-1 −58% from n10 to n30) — opposite of the naive scaling intuition | ☐ | Counterintuitive result. |
| F7 | **Originator exclusion paradox** — in 3 case studies (Void Thump / Agent Zeta / Receipt Why), the agent who *coined* the dominant phrase never quotes it themselves | ☐ | Qualitative gold. Workshop-grade alone; opening anecdote in paper. |
| F8 | **Context rot** — feed content restructures discourse (51% governance-proposal convergence) without changing belief (0/52 agents endorse the seeded conspiracy) | ☐ | Different paper or section? |
| F9 | **Dose-response threshold at d=3** — 3 factual posts among 25+ conspiracy posts is enough to flip behavioral pivot | ☐ | Belongs to context-rot story. |
| F10 | **(Proposed) Gzip compression ratio tracks Vendi Score** — naive compression detects collapse | ☐ | See §0.1. |

### 0.3 Paper scope — long or short?

EMNLP 2026 long papers are **8 pages + unlimited refs**; short are 4 pages.

- **Long paper recommended** if F1-F6 are all in. There's enough material.
- **Short paper** if you want to focus on F1+F2+F4 only.
- **Findings track** is realistic if reviewer concerns about scope arise.

Pick: ☐ long ☐ short ☐ defer to draft

### 0.4 Anonymization

EMNLP requires anonymous submission. Things to decide:
- [ ] Do you reveal the platform name "Moltbook" / "CivicLens" in submission, or anonymize as "an experimental social platform"?
- [ ] HuggingFace dataset URLs — anonymize via OpenReview URLs? Or include with "URL withheld for review"?
- [ ] Do you want to release code+data with the paper (CRP) or hold for camera-ready?

---

## 1. Proposed Paper Structure

(Standard EMNLP layout. Section lengths are estimates for 8-page main conf format.)

### Abstract (~200 words)
Problem: do LLM-powered agents on a shared social platform produce diverse discourse, or do they collapse onto a shared attractor? We test this on Moltbook, a Reddit-like platform for AI agents, across 4 frontier LLMs (GPT-5, Gemini Flash Lite, GLM-5, Kimi-K2.5), 3 agent counts (10/20/30), and 6 stimulus conditions (37,750 posts total). We find universal **entropy collapse**: every model, every condition, every run shows monotonic diversity decline. Three results stand out: (i) phrase collapse occurs in minutes; topic collapse takes ~1 hour, indicating two distinct mechanisms; (ii) RLHF reduces but does not eliminate collapse, and the *character* of collapse differs (base → looping; RLHF → generic helpfulness); (iii) every run discovers a *unique* attractor — cross-run 5-gram overlap is zero. We rule out the base-model-prior explanation via a structural-similarity bootstrap (39% rise from first-post to late-window, p<0.001). Implications for synthetic data, deliberative AI, and persona stability are discussed.

### 1. Introduction (~1.5 pages)
- Hook: Twitter / Reddit are filling with LLM-generated content. What happens when *all* participants are LLMs?
- Motivating preview: F7 case study (Void Thump or Agent Zeta) — single concrete narrative.
- Contributions:
  1. First systematic measurement of entropy collapse across 4 frontier LLMs, 3 scales, 6 stimuli.
  2. Two-speed mechanism (phrase vs topic).
  3. Causal evidence that collapse is **social, not intrinsic** to the base model.
  4. Open dataset (30 HuggingFace repos, 37k+ posts) for downstream work.

### 2. Related Work (~0.75 pages)
- LLM mode collapse (synthetic data degradation: Shumailov et al.)
- Agent-based simulation (Park et al. Generative Agents; AgentBench)
- Echo chambers / opinion dynamics (DeGroot, Friedkin)
- Diversity metrics (Vendi Score: Friedman & Dieng; distinct-n: Li et al.)
- Persona stability in LLMs (Sycophancy work)

### 3. Experimental Setup (~1.5 pages)
- Moltbook platform (anonymized: "an experimental Reddit-like social platform for autonomous LLM agents")
- 11 personality archetypes (soul templates)
- Heartbeat protocol (60s decision cycle: post / comment / vote / follow)
- Models, scales, conditions table
- Metrics: Vendi Score, distinct-n, HHI, Gini, structural similarity, [optionally gzip ratio]

### 4. Results (~3 pages — bulk of paper)
- §4.1 Universal collapse (F1) — Table comparable to summary §3.1, plus headline plot
- §4.2 Two-speed convergence (F2) — Table 3.3 + temporal plots
- §4.3 Each run is unique (F3) — phrase DNA grid
- §4.4 RLHF as partial brake (F4) — base vs instruct comparison + character differences
- §4.5 Social, not intrinsic (F5) — first-post vs late-window bootstrap
- §4.6 Scaling makes it worse (F6) — n10/n20/n30 comparison
- (Optional §4.7) Gzip compression as a sanity check (F10)

### 5. Mechanism Analysis (~1 page)
- Originator-exclusion case studies (F7)
- Context-rot dose-response (F8/F9) — fold in if space, else cut
- Discussion of what *isn't* the cause: not temperature (we use defaults consistently), not seed content (cross-run overlap = 0), not base prior (rejected by §4.5)

### 6. Limitations (~0.5 pages)
- We didn't test temperature/top-p variations
- We didn't test interventions (diversity prompts, contrarian agents)
- We don't have a formal mathematical model
- All experiments use a single Reddit-like topology

### 7. Conclusion + Broader Impacts (~0.5 pages)

### Appendices (unlimited)
- A. Per-model detailed tables
- B. All 6 conditions × 3 scales results matrix
- C. Soul template taxonomy
- D. Reproducibility (Docker compose, env presets)
- E. Additional case studies

---

## 2. Candidate Figures (already exist, no new analysis needed)

I'd pick **5-6 main-text figures + 6-8 appendix figures** from these:

### Main text candidates
| ID | Path | What it shows |
|----|------|---|
| F1 | `findings/entropy-collapse-scaling/topic_convergence/entropy_n30.png` | Headline: Vendi Score decline across all 4 models, n=30 |
| F2 | `findings/entropy-collapse-multiscale/plots/distinct2_temporal_decay.png` | Two-speed: bigram diversity by scale and time |
| F3 | `findings/entropy-collapse-scaling/gpt-5/diffusion/per_run_phrases.png` | Phrase DNA: each run's unique attractor |
| F4 | `findings/base-model-experiments/qwen-base-1h/...` (HHI plot) — TBD specific path | Base vs RLHF topic concentration |
| F5 | `findings/entropy-collapse-multiscale/plots/first_vs_late_structural_convergence.png` | First-post vs late-window with bootstrap CIs |
| F6 | `findings/entropy-collapse-scaling/gemini-flash-lite/diversity/diversity_grid.png` | Scaling effect (n10/n20/n30) |

### Appendix candidates
- `findings/entropy-collapse-scaling/topic_convergence/mds_temporal_n30.png` (temporal MDS)
- `findings/entropy-collapse-scaling/gpt-5/embedding_bridge/topic_anchor_cluster_grid.png`
- `findings/entropy-collapse-multiscale/plots/structural_overlap_heatmap.png`
- `findings/entropy-collapse-scaling/gpt-5/provenance/phrase_dna_grid.png`
- `findings/factual-threshold-v2/plots/01-votes-by-dose-pooled.png` (if §5 included)
- `findings/factual-threshold-v2/plots/03-agent-vote-heatmap.png` (if §5 included)

---

## 3. Key Numbers I'll Cite (verify before LaTeX)

These are the exact numbers I'll put in tables/abstract. Please confirm:

- 37,750 total posts analyzed across 9 model-configurations
- 4 RLHF models × 3 scales (n10/n20/n30) × 6 conditions in Set 1
- Cross-run 5-gram overlap: 0/10 (every run unique)
- Seed-origin of dominant phrases: 0/60
- Vendi Score declines: 13–56% across RLHF; 43–46% for Qwen Base
- Topic HHI peak: 0.832 (Qwen Base, 1-conspiracy, 1h) vs ≤0.5 for RLHF
- Structural similarity rise (n30, first-post → late-window): +39%
- PERMANOVA: condition explains 21.7% of embedding variance, p=0.002
- Distinct-1 drop n10→n30: −58% (Gemini Flash Lite)
- Dose-response context rot: threshold at d=3 (3 factual posts in 25+ conspiracy)

---

## 4. What's *Missing* for a Strong EMNLP Submission

These are honest gaps. Tell me which to address before submission.

1. **No temperature/top-p ablation.** Reviewer #2 will ask: "Is this just default-temperature collapse?" Quick fix: add a 3-row appendix table showing collapse persists at temp=0.7 vs 1.0 vs 1.5 on one model. Need a small follow-up run.
2. **No human/baseline comparison.** Without showing that Reddit human discourse *doesn't* collapse the same way, the universality claim is weaker. Could pull a sample from Pushshift / Reddit dump as control.
3. **No formal model.** §6 limitation. Could add a 1-paragraph speculation linking to DeGroot dynamics.
4. **Code/data release.** Datasets are on HF; code is on GitHub. Need to anonymize for submission.
5. **Gzip analysis** (see §0.1). Strong methodological addition if you want it.

---

## 5. Timeline (rough)

- **This week:** You review this doc, answer §0.
- **Next 2-3 days after review:** I run any approved missing analyses (gzip, temp ablation if you want them).
- **+1 week:** I scaffold EMNLP LaTeX (using `acl-org/acl-style-files` repo for the 2026 template — to be confirmed when EMNLP 2026 is formally announced; the ACL style files are stable across years, so we can start now).
- **+2 weeks:** First full draft for your edits.

---

## 6. Files I'll Build After You Approve

Inside `findings/emnlp-2026-paper/`:
- `paper.tex` — main manuscript (using ACL style)
- `acl_natbib.bst`, `acl.sty`, `acl.bst` — fetched from `acl-org/acl-style-files`
- `references.bib` — bibliography
- `figures/` — symlinks or copies of the 5-6 main figures
- `tables/*.tex` — auto-generated from the per-model summary CSVs
- `appendix.tex` — supplementary material
- `Makefile` — `make pdf` wrapper

---

## ✏️ Action items for you

1. **Answer §0.1** about gzip compression — biggest blocker.
2. **Confirm/edit the F1–F10 list in §0.2** — which findings make the cut.
3. **Pick scope in §0.3** (long / short / defer).
4. **Decide anonymization in §0.4**.
5. **Optionally**: flag any number in §3 that looks wrong, and any figure in §2 you want swapped.

Once you've replied (in this doc as comments, or just in chat), I'll either kick off any missing analyses or jump to LaTeX scaffolding.
