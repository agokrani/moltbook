# Step 7: exact n-grams are conservative

Finding 8 asks what exact NLTK 5-gram matching misses.

## Scope

- Agent-generated posts only
- Exact NLTK 5-token anchors
- Punctuation and casing retained
- Stopwords retained
- No stemming
- No lemmatization
- No lowercasing
- No fuzzy matching
- Seed rows are excluded before matching

## Output

- `exact_ngram_conservatism_table.png/pdf`
- `exact_ngram_conservatism_examples.csv`
- `exact_ngram_conservatism_audit_counts.csv`
- `exact_ngram_conservatism_audit_overlaps.csv`
- `exact_ngram_conservatism_audit_records.csv`
- `summary.json`

## Examples

| Motif | Strict anchor | Strict posts | Family lower-bound posts | Added posts | Lesson |
|---|---|---:|---:|---:|---|
| Claim-checking template | Claim (1 line) | 84 | 126 | +42 | Casing and punctuation/context windows split one template into several exact anchors. |
| Bucket role-play motif | Kappa, the bucket is | 16 | 49 | +33 | Small determiner changes create separate exact anchors for the same role-play object. |
| Questions attribution motif | questions that abandon us. | 32 | 39 | +7 | Citation frames around the phrase are socially related but exact matching counts them separately. |
