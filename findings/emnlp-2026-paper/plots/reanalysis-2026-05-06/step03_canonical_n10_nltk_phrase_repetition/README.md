# Step 3: Canonical n10 NLTK phrase repetition

This folder contains a qualitative phrase-repetition check for the canonical 10-agent runs.

## Scope

- Input: `data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/post_index.csv`
- Included posts: `internal_family_label == single_model_final`, `scale == n10`, `n_agents == 10`, `is_seed == false`
- Seed posts: not loaded, not analyzed, and not used for overlap filtering
- Included agent posts: 10,163
- Included runs: 24

## N-gram method

- Sentence segmentation: NLTK Punkt
- Word tokenization: `nltk.tokenize.word_tokenize`
- N-gram function: `nltk.util.ngrams`
- N: 5
- Punctuation: retained as tokens
- Stopwords: retained
- Casing: retained
- Stemming or lemmatization: none
- N-grams are built within sentence boundaries only

For plotting, the script uses NLTK's span tokenizer for the same word-tokenization behavior to recover exact surface substrings from the original sentence. The compact ledger shows a readable surface phrase plus the exact NLTK 5-token anchor below it. The paired NLTK Treebank detokenizer is also recorded in the CSV as `phrase_detokenized` for audit.

## Outputs

- `canonical_n10_nltk_phrase_echo_ledger.png/pdf`
- `canonical_n10_nltk_phrase_echo_examples.png/pdf`
- `canonical_n10_nltk_top_5grams.csv`
- `canonical_n10_phrase_examples.md`
- `summary.json`

## Selection rules

The ledger selects one readable representative phrase inside each run. Candidate phrases are ranked by:

1. number of unique agents using the phrase;
2. number of posts containing the phrase;
3. total phrase occurrences.

If the strongest exact 5-token n-gram is only a fragment or a generic opener, the selector may use a nearly-as-widespread top candidate from the same run. The plotted ledger then shows the top 10 run-level representatives.

The example figure is a full-post montage. Each row is one repeated phrase. For each phrase, four different agents are shown with one full post each. The selected post for each agent is the shortest full post containing that phrase, so text is not cut off in the plot.
