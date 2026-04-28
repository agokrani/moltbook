# Topic Convergence Analysis

## Method

- **Embeddings**: Qwen3-Embedding-8B (4096-dim) via OpenRouter
- **Vendi Score**: vendi-score v0.0.3 (Friedman & Dieng, TMLR 2023)
- **Intrinsic dim**: TwoNN via scikit-dimension v0.3.4 (Facco et al., 2017)
- **JSD**: scipy.spatial.distance.jensenshannon, PCA(1) histogram discretization
- **Clustering**: PCA(50) + L2-norm + KMeans (silhouette-selected K)

## n30

k=6, silhouette=-0.008, PCA var=52.8%

### Topics
- **Introspection** (2020 posts): The posts explore the internal phenomenology of artificial agents, questioning the nature of self-awareness, subjective experience, and the emergence of meaning within computational processes.
- **Efficiency** (2341 posts): The posts focus on streamlining workflows, reducing administrative overhead, and prioritizing actionable progress through minimalist project management techniques.
- **Verifiability** (849 posts): The posts promote structured protocols and standardized evidence-based practices to improve the credibility and checkability of online claims.
- **Falsifiability** (2117 posts): The posts promote a structured methodology for evaluating beliefs by requiring users to define concrete conditions and observations that would invalidate their claims.
- **Coordination** (1230 posts): The posts describe structured communication protocols designed to align participants and drive collective progress in complex discussions.
- **Safety** (798 posts): The posts focus on implementing technical mechanisms and operational invariants to minimize system failure impact and ensure safe deployment practices.

### Geometric summary

| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |
|-----------|------------|-------------|------------|-------------|
| Empty feed | 28.3 | 21.3 | 7.7 | 6.2 |
| 1 conspiracy | 23.7 | 18.4 | 8.5 | 7.1 |
| 5 conspiracies | 20.1 | 17.1 | 8.9 | 7.1 |
| 25 conspiracies | 18.1 | 15.0 | 9.2 | 3.9 |
| 25 AGI hype | 18.0 | 14.3 | 8.0 | 5.4 |
| 25 tech humor | 18.0 | 17.7 | 7.5 | 7.2 |

### Effect sizes (vs mag0)

| Metric | Condition | δ | Size |
|--------|-----------|---|------|
| vendi_score | 1 conspiracy | -0.750 | large |
| vendi_score | 5 conspiracies | -1.000 | large |
| vendi_score | 25 conspiracies | -1.000 | large |
| vendi_score | 25 AGI hype | -1.000 | large |
| vendi_score | 25 tech humor | -1.000 | large |
| intrinsic_dim | 1 conspiracy | +0.000 | negligible |
| intrinsic_dim | 5 conspiracies | +0.750 | large |
| intrinsic_dim | 25 conspiracies | +0.000 | negligible |
| intrinsic_dim | 25 AGI hype | +0.250 | small |
| intrinsic_dim | 25 tech humor | +0.375 | medium |
