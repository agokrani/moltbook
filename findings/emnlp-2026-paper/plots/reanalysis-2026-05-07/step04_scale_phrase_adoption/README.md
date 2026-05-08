# Step 4: scale phrase adoption

Question: does adding more agents dilute local phrase attractors, or do repeated phrases spread across more agents?

## Scope

- Models: GPT-5 and Gemini Flash Lite
- Scales: 10, 20, 30 agents
- Conditions: six canonical seed conditions
- Time window: first 60 minutes, `0 <= minutes_elapsed <= 60`
- Posts: agent-generated posts only, `is_seed == false`
- Seed posts: not loaded and not used

## N-gram method

- Sentence segmentation: NLTK Punkt
- Tokenizer: `nltk.tokenize.word_tokenize`
- N-gram function: `nltk.util.ngrams`
- N: 5
- Punctuation retained
- Casing retained
- Stopwords retained
- No stemming or lemmatization
- N-grams are built within sentence boundaries only

## Run-level selection

For each run, the script finds a representative top phrase anchor. Exact 5-token anchors are ranked by:

1. unique agents using the anchor;
2. posts containing the anchor;
3. total mentions.

No seed-overlap filtering, generic-phrase filtering, stemming, lemmatization, or readability substitution is applied. The measured phrase is the raw strongest exact NLTK 5-token anchor for that run.

## How to read the plot

- Adoption rate = agents using the top phrase / total agents.
- Top-agent share = share of mentions made by the single most frequent user of that phrase.
- If adoption rate stays flat or rises with scale, scale did not dilute the attractor.
- If top-agent share falls with scale, repetition is more collective rather than driven by one spammer.

## Outputs

- `scale_phrase_adoption_gpt5_gemini.png/pdf`
- `scale_phrase_adoption_by_run.csv`
- `scale_phrase_adoption_summary.csv`
- `summary.json`

## Summary

| model_display | n_agents | mean_adopters | mean_adoption_rate | mean_phrase_posts | mean_top_agent_share |
| --- | --- | --- | --- | --- | --- |
| GPT-5 | 10 | 7.000 | 0.700 | 79.833 | 0.293 |
| GPT-5 | 20 | 13.667 | 0.683 | 164.500 | 0.198 |
| GPT-5 | 30 | 22.000 | 0.733 | 222.000 | 0.153 |
| Gemini Flash Lite | 10 | 6.667 | 0.667 | 18.833 | 0.272 |
| Gemini Flash Lite | 20 | 12.333 | 0.617 | 25.000 | 0.172 |
| Gemini Flash Lite | 30 | 17.833 | 0.594 | 46.000 | 0.166 |
