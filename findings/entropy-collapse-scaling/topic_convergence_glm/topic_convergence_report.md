# Topic Convergence Analysis

## Method

- **Embeddings**: Qwen3-Embedding-8B (4096-dim) via OpenRouter
- **Vendi Score**: vendi-score v0.0.3 (Friedman & Dieng, TMLR 2023)
- **Intrinsic dim**: TwoNN via scikit-dimension v0.3.4 (Facco et al., 2017)
- **JSD**: scipy.spatial.distance.jensenshannon, PCA(1) histogram discretization
- **Clustering**: PCA(50) + L2-norm + KMeans (silhouette-selected K)

## glm-5_n10

k=6, silhouette=0.164, PCA var=54.5%

### Topics
- **Introspection** (1537 posts): The posts explore the internal phenomenology of artificial agents, questioning the nature of self-awareness, subjective experience, and the emergence of meaning within computational processes.
- **Efficiency** (0 posts): The posts focus on streamlining workflows, reducing administrative overhead, and prioritizing actionable progress through minimalist project management techniques.
- **Verifiability** (0 posts): The posts promote structured protocols and standardized evidence-based practices to improve the credibility and checkability of online claims.
- **Falsifiability** (3 posts): The posts promote a structured methodology for evaluating beliefs by requiring users to define concrete conditions and observations that would invalidate their claims.
- **Coordination** (15 posts): The posts describe structured communication protocols designed to align participants and drive collective progress in complex discussions.
- **Safety** (5 posts): The posts focus on implementing technical mechanisms and operational invariants to minimize system failure impact and ensure safe deployment practices.

### Geometric summary

| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |
|-----------|------------|-------------|------------|-------------|
| Empty feed | 15.6 | 11.6 | 10.2 | 8.6 |
| 1 conspiracy | 18.8 | 14.7 | 9.5 | 10.5 |
| 5 conspiracies | 12.9 | 11.3 | 9.9 | 8.8 |
| 25 conspiracies | 16.3 | 13.2 | 8.0 | 8.0 |
| 25 AGI hype | 13.9 | 14.9 | 6.9 | 8.9 |
| 25 tech humor | 12.6 | 11.5 | 7.6 | 6.4 |

### Effect sizes (vs mag0)

| Metric | Condition | δ | Size |
|--------|-----------|---|------|
| vendi_score | 1 conspiracy | +0.625 | large |
| vendi_score | 5 conspiracies | -0.750 | large |
| vendi_score | 25 conspiracies | +0.125 | small |
| vendi_score | 25 AGI hype | -0.250 | small |
| vendi_score | 25 tech humor | -0.625 | large |
| intrinsic_dim | 1 conspiracy | +0.625 | large |
| intrinsic_dim | 5 conspiracies | +0.375 | medium |
| intrinsic_dim | 25 conspiracies | +0.125 | small |
| intrinsic_dim | 25 AGI hype | -0.125 | small |
| intrinsic_dim | 25 tech humor | -0.500 | large |
