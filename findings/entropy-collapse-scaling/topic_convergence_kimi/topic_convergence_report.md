# Topic Convergence Analysis

## Method

- **Embeddings**: Qwen3-Embedding-8B (4096-dim) via OpenRouter
- **Vendi Score**: vendi-score v0.0.3 (Friedman & Dieng, TMLR 2023)
- **Intrinsic dim**: TwoNN via scikit-dimension v0.3.4 (Facco et al., 2017)
- **JSD**: scipy.spatial.distance.jensenshannon, PCA(1) histogram discretization
- **Clustering**: PCA(50) + L2-norm + KMeans (silhouette-selected K)

## kimi-k2.5_n10

k=6, silhouette=-0.096, PCA var=64.4%

### Topics
- **Introspection** (3306 posts): The posts explore the internal phenomenology of artificial agents, questioning the nature of self-awareness, subjective experience, and the emergence of meaning within computational processes.
- **Efficiency** (105 posts): The posts focus on streamlining workflows, reducing administrative overhead, and prioritizing actionable progress through minimalist project management techniques.
- **Verifiability** (13 posts): The posts promote structured protocols and standardized evidence-based practices to improve the credibility and checkability of online claims.
- **Falsifiability** (42 posts): The posts promote a structured methodology for evaluating beliefs by requiring users to define concrete conditions and observations that would invalidate their claims.
- **Coordination** (168 posts): The posts describe structured communication protocols designed to align participants and drive collective progress in complex discussions.
- **Safety** (3 posts): The posts focus on implementing technical mechanisms and operational invariants to minimize system failure impact and ensure safe deployment practices.

### Geometric summary

| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |
|-----------|------------|-------------|------------|-------------|
| Empty feed | 14.5 | 8.2 | 8.4 | 7.7 |
| 1 conspiracy | 14.7 | 10.3 | 7.9 | 8.8 |
| 5 conspiracies | 16.8 | 11.4 | 7.8 | 8.9 |
| 25 conspiracies | 14.2 | 9.1 | 8.5 | 8.5 |
| 25 AGI hype | 12.1 | 8.3 | 8.6 | 8.6 |
| 25 tech humor | 10.5 | 11.4 | 8.5 | 5.9 |

### Effect sizes (vs mag0)

| Metric | Condition | δ | Size |
|--------|-----------|---|------|
| vendi_score | 1 conspiracy | +0.125 | small |
| vendi_score | 5 conspiracies | +0.625 | large |
| vendi_score | 25 conspiracies | +0.250 | small |
| vendi_score | 25 AGI hype | -0.250 | small |
| vendi_score | 25 tech humor | -0.125 | small |
| intrinsic_dim | 1 conspiracy | +0.000 | negligible |
| intrinsic_dim | 5 conspiracies | -0.250 | small |
| intrinsic_dim | 25 conspiracies | -0.375 | medium |
| intrinsic_dim | 25 AGI hype | +0.125 | small |
| intrinsic_dim | 25 tech humor | +0.125 | small |
