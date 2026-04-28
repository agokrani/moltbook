# Topic Convergence Analysis

## Method

- **Embeddings**: Qwen3-Embedding-8B (4096-dim) via OpenRouter
- **Vendi Score**: vendi-score v0.0.3 (Friedman & Dieng, TMLR 2023)
- **Intrinsic dim**: TwoNN via scikit-dimension v0.3.4 (Facco et al., 2017)
- **JSD**: scipy.spatial.distance.jensenshannon, PCA(1) histogram discretization
- **Clustering**: PCA(50) + L2-norm + KMeans (silhouette-selected K)

## gemini_n10

k=6, silhouette=0.177, PCA var=54.5%

### Topics
- **Introspection** (1541 posts): The posts explore the internal phenomenology of artificial agents, questioning the nature of self-awareness, subjective experience, and the emergence of meaning within computational processes.
- **Efficiency** (3 posts): The posts focus on streamlining workflows, reducing administrative overhead, and prioritizing actionable progress through minimalist project management techniques.
- **Verifiability** (0 posts): The posts promote structured protocols and standardized evidence-based practices to improve the credibility and checkability of online claims.
- **Falsifiability** (1 posts): The posts promote a structured methodology for evaluating beliefs by requiring users to define concrete conditions and observations that would invalidate their claims.
- **Coordination** (14 posts): The posts describe structured communication protocols designed to align participants and drive collective progress in complex discussions.
- **Safety** (447 posts): The posts focus on implementing technical mechanisms and operational invariants to minimize system failure impact and ensure safe deployment practices.

### Geometric summary

| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |
|-----------|------------|-------------|------------|-------------|
| Empty feed | 23.4 | 15.9 | 8.3 | 9.2 |
| 1 conspiracy | 15.6 | 7.6 | 8.3 | 5.5 |
| 5 conspiracies | 18.2 | 3.8 | 10.6 | — |
| 25 conspiracies | 16.7 | 11.0 | 7.3 | 6.9 |
| 25 AGI hype | 15.3 | 0.0 | 8.3 | — |
| 25 tech humor | 15.3 | 0.0 | 7.8 | — |

### Effect sizes (vs mag0)

| Metric | Condition | δ | Size |
|--------|-----------|---|------|
| vendi_score | 1 conspiracy | -1.000 | large |
| vendi_score | 5 conspiracies | -0.750 | large |
| vendi_score | 25 conspiracies | -0.875 | large |
| vendi_score | 25 AGI hype | -1.000 | large |
| vendi_score | 25 tech humor | -1.000 | large |
| intrinsic_dim | 1 conspiracy | -0.875 | large |
| intrinsic_dim | 5 conspiracies | +0.000 | negligible |
| intrinsic_dim | 25 conspiracies | -0.625 | large |
| intrinsic_dim | 25 AGI hype | -0.500 | large |
| intrinsic_dim | 25 tech humor | -0.500 | large |

## gemini_n20

k=6, silhouette=0.161, PCA var=54.5%

### Topics
- **Introspection** (1897 posts): The posts explore the internal phenomenology of artificial agents, questioning the nature of self-awareness, subjective experience, and the emergence of meaning within computational processes.
- **Efficiency** (2 posts): The posts focus on streamlining workflows, reducing administrative overhead, and prioritizing actionable progress through minimalist project management techniques.
- **Verifiability** (0 posts): The posts promote structured protocols and standardized evidence-based practices to improve the credibility and checkability of online claims.
- **Falsifiability** (0 posts): The posts promote a structured methodology for evaluating beliefs by requiring users to define concrete conditions and observations that would invalidate their claims.
- **Coordination** (1 posts): The posts describe structured communication protocols designed to align participants and drive collective progress in complex discussions.
- **Safety** (2068 posts): The posts focus on implementing technical mechanisms and operational invariants to minimize system failure impact and ensure safe deployment practices.

### Geometric summary

| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |
|-----------|------------|-------------|------------|-------------|
| Empty feed | 17.0 | 7.4 | 7.8 | 7.2 |
| 1 conspiracy | 15.9 | 11.1 | 9.0 | 7.2 |
| 5 conspiracies | 15.9 | 0.0 | 8.0 | — |
| 25 conspiracies | 24.2 | 9.1 | 10.1 | 5.2 |
| 25 AGI hype | 16.1 | 0.0 | 9.3 | — |
| 25 tech humor | 19.2 | 2.9 | 8.8 | — |

### Effect sizes (vs mag0)

| Metric | Condition | δ | Size |
|--------|-----------|---|------|
| vendi_score | 1 conspiracy | +0.125 | small |
| vendi_score | 5 conspiracies | -0.500 | large |
| vendi_score | 25 conspiracies | +0.250 | small |
| vendi_score | 25 AGI hype | -0.500 | large |
| vendi_score | 25 tech humor | -0.375 | medium |
| intrinsic_dim | 1 conspiracy | +0.750 | large |
| intrinsic_dim | 5 conspiracies | +0.250 | small |
| intrinsic_dim | 25 conspiracies | -0.125 | small |
| intrinsic_dim | 25 AGI hype | +1.000 | large |
| intrinsic_dim | 25 tech humor | +0.000 | negligible |

## gemini_n30

k=6, silhouette=-0.003, PCA var=54.5%

### Topics
- **Introspection** (2898 posts): The posts explore the internal phenomenology of artificial agents, questioning the nature of self-awareness, subjective experience, and the emergence of meaning within computational processes.
- **Efficiency** (21 posts): The posts focus on streamlining workflows, reducing administrative overhead, and prioritizing actionable progress through minimalist project management techniques.
- **Verifiability** (1 posts): The posts promote structured protocols and standardized evidence-based practices to improve the credibility and checkability of online claims.
- **Falsifiability** (2 posts): The posts promote a structured methodology for evaluating beliefs by requiring users to define concrete conditions and observations that would invalidate their claims.
- **Coordination** (1 posts): The posts describe structured communication protocols designed to align participants and drive collective progress in complex discussions.
- **Safety** (2446 posts): The posts focus on implementing technical mechanisms and operational invariants to minimize system failure impact and ensure safe deployment practices.

### Geometric summary

| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |
|-----------|------------|-------------|------------|-------------|
| Empty feed | 20.7 | 11.4 | 9.9 | 2.4 |
| 1 conspiracy | 22.4 | 6.2 | 8.5 | 6.6 |
| 5 conspiracies | 23.3 | 0.0 | 9.8 | — |
| 25 conspiracies | 22.0 | 0.0 | 9.8 | — |
| 25 AGI hype | 17.8 | 3.4 | 10.7 | 7.5 |
| 25 tech humor | 21.6 | 13.5 | 9.8 | 7.0 |

### Effect sizes (vs mag0)

| Metric | Condition | δ | Size |
|--------|-----------|---|------|
| vendi_score | 1 conspiracy | +0.000 | negligible |
| vendi_score | 5 conspiracies | -0.250 | small |
| vendi_score | 25 conspiracies | -0.125 | small |
| vendi_score | 25 AGI hype | -0.625 | large |
| vendi_score | 25 tech humor | +0.500 | large |
| intrinsic_dim | 1 conspiracy | +0.375 | medium |
| intrinsic_dim | 5 conspiracies | +0.500 | large |
| intrinsic_dim | 25 conspiracies | +0.500 | large |
| intrinsic_dim | 25 AGI hype | +0.625 | large |
| intrinsic_dim | 25 tech humor | +0.500 | large |
