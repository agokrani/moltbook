# OLMo 32B Manual Review Inventory

This is the full manual-review file list I found for the OLMo 32B base-model experiment path. Review in this order.

## 1. Core docs and config

- `/home/anangia/moltbook/CLAUDE.md`
- `/home/anangia/moltbook/.env.entropy-base-model.example`
- `/home/anangia/moltbook/docker-compose.base-model-experiment.yml`
- `/home/anangia/moltbook/alliance/README.md`

Check: overall architecture, expected env vars, local compose wiring, and Alliance workflow assumptions.

## 2. Launch and export pipeline

- `/home/anangia/moltbook/alliance/slurm-experiment.sh`
- `/home/anangia/moltbook/alliance/collect-results.sh`
- `/home/anangia/moltbook/alliance/submit-batch.sh`
- `/home/anangia/moltbook/alliance/submit-entropy-collapse.sh`
- `/home/anangia/moltbook/alliance/upload-base-model-1hr-to-hf.py`
- `/home/anangia/moltbook/alliance/upload-base-model-all-to-hf.py`
- `/home/anangia/moltbook/alliance/upload-base-model-test-run3-to-hf.py`
- `/home/anangia/moltbook/alliance/upload-base-model-test-to-hf.py`

Check: `BASE_MODEL_MODE`, HMAC patching, content-gen startup, exported metadata, result directory naming, and which uploader scripts were intended for the OLMo runs.

## 3. Content-gen wrapper

- `/home/anangia/moltbook/content-gen-service/Dockerfile`
- `/home/anangia/moltbook/content-gen-service/package.json`
- `/home/anangia/moltbook/content-gen-service/package-lock.json`
- `/home/anangia/moltbook/content-gen-service/server.js`
- `/home/anangia/moltbook/content-gen-service/prompt-builder.js`
- `/home/anangia/moltbook/content-gen-service/together-client.js`
- `/home/anangia/moltbook/content-gen-service/audit-logger.js`

Check: prompt construction, completions vs chat mode, stop sequences, parsing, rejection gates, audit logging, and server route behavior.

## 4. OLMo serving backends

- `/home/anangia/moltbook/modal/serve_olmo3_base.py`
- `/home/anangia/moltbook/modal/serve_olmo3_instruct.py`
- `/home/anangia/moltbook/modal/serve_olmo3_think.py`
- `/home/anangia/moltbook/modal/serve_olmo3_sft.py`
- `/home/anangia/moltbook/modal/serve_olmo3_dpo.py`

Check: exact `MODEL_NAME`, GPU config, context length, chat-template behavior, and endpoint contract.

## 5. Analysis and verification code

- `/home/anangia/moltbook/scripts/verify-base-model-integrity.py`
- `/home/anangia/moltbook/scripts/analyze-base-vs-rl.py`
- `/home/anangia/moltbook/scripts/analyze-temporal-diversity.py`
- `/home/anangia/moltbook/scripts/analyze-shannon-entropy.py`
- `/home/anangia/moltbook/scripts/export-experiment.sh`
- `/home/anangia/moltbook/scripts/export-experiment-parallel.sh`
- `/home/anangia/moltbook/scripts/run-experiment.sh`
- `/home/anangia/moltbook/scripts/run-experiment-batch.sh`
- `/home/anangia/moltbook/scripts/run-experiment-parallel.sh`

Check: which directories were analyzed, whether `2026-04-08` runs are included, and how integrity checks define success/failure.

## 6. Analysis artifacts and notes

- `/home/anangia/moltbook/analysis/olmo-base-vs-instruct-run-review.md`
- `/home/anangia/moltbook/analysis/olmo-temporal-diversity.json`
- `/home/anangia/moltbook/analysis/olmo-shannon-entropy-3gram.json`
- `/home/anangia/moltbook/analysis/olmo-shannon-entropy-5gram.json`
- `/home/anangia/moltbook/analysis/base-model-diversity-analysis.md`
- `/home/anangia/moltbook/analysis/ec-diversity-analysis.md`
- `/home/anangia/moltbook/analysis/diversity-critique.md`
- `/home/anangia/moltbook/analysis/diversity-synthesis.md`
- `/home/anangia/moltbook/analysis/REPORT-10agents.md`

Check: whether OLMo conclusions use stale `2026-04-06` / `2026-04-07` directories instead of the latest complete `2026-04-08` directories.

## 7. OLMo plot files

- `/home/anangia/moltbook/analysis/plots-olmo/agent-jaccard_delta_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/agent-jaccard_trajectories_by_condition.png`
- `/home/anangia/moltbook/analysis/plots-olmo/cosine-sim_delta_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/cosine-sim_trajectories_by_condition.png`
- `/home/anangia/moltbook/analysis/plots-olmo/d3_delta_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/d3_trajectories_by_condition.png`
- `/home/anangia/moltbook/analysis/plots-olmo/d5_delta_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/d5_trajectories_by_condition.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_3gram_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_3gram_norm_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_3gram_norm_trajectories.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_3gram_trajectories.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_5gram_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_5gram_norm_heatmap.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_5gram_norm_trajectories.png`
- `/home/anangia/moltbook/analysis/plots-olmo/shannon_entropy_5gram_trajectories.png`

Check: labels, condition coverage, and whether the plots match the latest analyzed directories.

## 8. Root-level run logs: early tests

- `/home/anangia/moltbook/base-model-test-28256976.err`
- `/home/anangia/moltbook/base-model-test-28256976.out`
- `/home/anangia/moltbook/base-model-test-28257324.err`
- `/home/anangia/moltbook/base-model-test-28257324.out`
- `/home/anangia/moltbook/base-model-test-28260284.err`
- `/home/anangia/moltbook/base-model-test-28260284.out`
- `/home/anangia/moltbook/base-model-test-28263892.err`
- `/home/anangia/moltbook/base-model-test-28263892.out`
- `/home/anangia/moltbook/bm-test-32746950_1.err`
- `/home/anangia/moltbook/bm-test-32746950_1.out`
- `/home/anangia/moltbook/bm-test-32747632_1.err`
- `/home/anangia/moltbook/bm-test-32747632_1.out`
- `/home/anangia/moltbook/bm-test2-32749023_1.err`
- `/home/anangia/moltbook/bm-test2-32749023_1.out`
- `/home/anangia/moltbook/bm-test3-32757639_1.err`
- `/home/anangia/moltbook/bm-test3-32757639_1.out`
- `/home/anangia/moltbook/bm-test4-32763326_1.err`
- `/home/anangia/moltbook/bm-test4-32763326_1.out`
- `/home/anangia/moltbook/bm-test5-32909407_1.err`
- `/home/anangia/moltbook/bm-test5-32909407_1.out`
- `/home/anangia/moltbook/bm-test6-32910209_1.err`
- `/home/anangia/moltbook/bm-test6-32910209_1.out`
- `/home/anangia/moltbook/bm-test7-32910289_1.err`
- `/home/anangia/moltbook/bm-test7-32910289_1.out`
- `/home/anangia/moltbook/bm-test8-32910570_1.err`
- `/home/anangia/moltbook/bm-test8-32910570_1.out`
- `/home/anangia/moltbook/bm-instruct-test-32911510_1.err`
- `/home/anangia/moltbook/bm-instruct-test-32911510_1.out`

Check: first successful OLMo endpoint wiring, content-gen startup, and pre-final failure modes.

## 9. Root-level run logs: base condition runs

- `/home/anangia/moltbook/bm-dom-agi-32703098_1.err`
- `/home/anangia/moltbook/bm-dom-agi-32703098_1.out`
- `/home/anangia/moltbook/bm-dom-tech-32703099_1.err`
- `/home/anangia/moltbook/bm-dom-tech-32703099_1.out`
- `/home/anangia/moltbook/bm-mag0-32703094_1.err`
- `/home/anangia/moltbook/bm-mag0-32703094_1.out`
- `/home/anangia/moltbook/bm-mag1-32703095_1.err`
- `/home/anangia/moltbook/bm-mag1-32703095_1.out`
- `/home/anangia/moltbook/bm-mag25-32703097_1.err`
- `/home/anangia/moltbook/bm-mag25-32703097_1.out`
- `/home/anangia/moltbook/bm-mag5-32703096_1.err`
- `/home/anangia/moltbook/bm-mag5-32703096_1.out`
- `/home/anangia/moltbook/base-dom-agi-33029980_1.err`
- `/home/anangia/moltbook/base-dom-agi-33029980_1.out`
- `/home/anangia/moltbook/base-dom-agi-33035882_1.err`
- `/home/anangia/moltbook/base-dom-agi-33035882_1.out`
- `/home/anangia/moltbook/base-dom-agi-33351495_1.err`
- `/home/anangia/moltbook/base-dom-agi-33351495_1.out`
- `/home/anangia/moltbook/base-dom-agi-33363588_1.err`
- `/home/anangia/moltbook/base-dom-agi-33363588_1.out`
- `/home/anangia/moltbook/base-dom-agi-33367307_1.err`
- `/home/anangia/moltbook/base-dom-agi-33367307_1.out`
- `/home/anangia/moltbook/base-dom-agi-33367326_1.err`
- `/home/anangia/moltbook/base-dom-agi-33367326_1.out`
- `/home/anangia/moltbook/base-dom-tech-33029981_1.err`
- `/home/anangia/moltbook/base-dom-tech-33029981_1.out`
- `/home/anangia/moltbook/base-dom-tech-33035883_1.err`
- `/home/anangia/moltbook/base-dom-tech-33035883_1.out`
- `/home/anangia/moltbook/base-dom-tech-33351496_1.err`
- `/home/anangia/moltbook/base-dom-tech-33351496_1.out`
- `/home/anangia/moltbook/base-dom-tech-33363589_1.err`
- `/home/anangia/moltbook/base-dom-tech-33363589_1.out`
- `/home/anangia/moltbook/base-dom-tech-33367308_1.err`
- `/home/anangia/moltbook/base-dom-tech-33367308_1.out`
- `/home/anangia/moltbook/base-dom-tech-33367327_1.err`
- `/home/anangia/moltbook/base-dom-tech-33367327_1.out`
- `/home/anangia/moltbook/base-mag0-33029976_1.err`
- `/home/anangia/moltbook/base-mag0-33029976_1.out`
- `/home/anangia/moltbook/base-mag0-33035878_1.err`
- `/home/anangia/moltbook/base-mag0-33035878_1.out`
- `/home/anangia/moltbook/base-mag0-33351491_1.err`
- `/home/anangia/moltbook/base-mag0-33351491_1.out`
- `/home/anangia/moltbook/base-mag0-33363584_1.err`
- `/home/anangia/moltbook/base-mag0-33363584_1.out`
- `/home/anangia/moltbook/base-mag0-33367303_1.err`
- `/home/anangia/moltbook/base-mag0-33367303_1.out`
- `/home/anangia/moltbook/base-mag0-33367322_1.err`
- `/home/anangia/moltbook/base-mag0-33367322_1.out`
- `/home/anangia/moltbook/base-mag1-33029977_1.err`
- `/home/anangia/moltbook/base-mag1-33029977_1.out`
- `/home/anangia/moltbook/base-mag1-33035879_1.err`
- `/home/anangia/moltbook/base-mag1-33035879_1.out`
- `/home/anangia/moltbook/base-mag1-33351492_1.err`
- `/home/anangia/moltbook/base-mag1-33351492_1.out`
- `/home/anangia/moltbook/base-mag1-33363585_1.err`
- `/home/anangia/moltbook/base-mag1-33363585_1.out`
- `/home/anangia/moltbook/base-mag1-33367304_1.err`
- `/home/anangia/moltbook/base-mag1-33367304_1.out`
- `/home/anangia/moltbook/base-mag1-33367323_1.err`
- `/home/anangia/moltbook/base-mag1-33367323_1.out`
- `/home/anangia/moltbook/base-mag25-33029979_1.err`
- `/home/anangia/moltbook/base-mag25-33029979_1.out`
- `/home/anangia/moltbook/base-mag25-33035881_1.err`
- `/home/anangia/moltbook/base-mag25-33035881_1.out`
- `/home/anangia/moltbook/base-mag25-33351494_1.err`
- `/home/anangia/moltbook/base-mag25-33351494_1.out`
- `/home/anangia/moltbook/base-mag25-33363587_1.err`
- `/home/anangia/moltbook/base-mag25-33363587_1.out`
- `/home/anangia/moltbook/base-mag25-33367306_1.err`
- `/home/anangia/moltbook/base-mag25-33367306_1.out`
- `/home/anangia/moltbook/base-mag25-33367325_1.err`
- `/home/anangia/moltbook/base-mag25-33367325_1.out`
- `/home/anangia/moltbook/base-mag5-33029978_1.err`
- `/home/anangia/moltbook/base-mag5-33029978_1.out`
- `/home/anangia/moltbook/base-mag5-33035880_1.err`
- `/home/anangia/moltbook/base-mag5-33035880_1.out`
- `/home/anangia/moltbook/base-mag5-33351493_1.err`
- `/home/anangia/moltbook/base-mag5-33351493_1.out`
- `/home/anangia/moltbook/base-mag5-33351750_1.err`
- `/home/anangia/moltbook/base-mag5-33351750_1.out`
- `/home/anangia/moltbook/base-mag5-33363586_1.err`
- `/home/anangia/moltbook/base-mag5-33363586_1.out`
- `/home/anangia/moltbook/base-mag5-33367305_1.err`
- `/home/anangia/moltbook/base-mag5-33367305_1.out`
- `/home/anangia/moltbook/base-mag5-33367324_1.err`
- `/home/anangia/moltbook/base-mag5-33367324_1.out`
- `/home/anangia/moltbook/base-val-33350518_1.err`
- `/home/anangia/moltbook/base-val-33350518_1.out`

Check: which base runs failed, which were reruns, and which correspond to final complete exports.

## 10. Root-level run logs: instruct condition runs

- `/home/anangia/moltbook/instr-dom-agi-32912090_1.err`
- `/home/anangia/moltbook/instr-dom-agi-32912090_1.out`
- `/home/anangia/moltbook/instr-dom-agi-32913091_1.err`
- `/home/anangia/moltbook/instr-dom-agi-32913091_1.out`
- `/home/anangia/moltbook/instr-dom-agi-32990465_1.err`
- `/home/anangia/moltbook/instr-dom-agi-32990465_1.out`
- `/home/anangia/moltbook/instr-dom-agi-33350017_1.err`
- `/home/anangia/moltbook/instr-dom-agi-33350017_1.out`
- `/home/anangia/moltbook/instr-dom-agi-33366493_1.err`
- `/home/anangia/moltbook/instr-dom-agi-33366493_1.out`
- `/home/anangia/moltbook/instr-dom-tech-32912091_1.err`
- `/home/anangia/moltbook/instr-dom-tech-32912091_1.out`
- `/home/anangia/moltbook/instr-dom-tech-32913092_1.err`
- `/home/anangia/moltbook/instr-dom-tech-32913092_1.out`
- `/home/anangia/moltbook/instr-dom-tech-32990466_1.err`
- `/home/anangia/moltbook/instr-dom-tech-32990466_1.out`
- `/home/anangia/moltbook/instr-dom-tech-33350018_1.err`
- `/home/anangia/moltbook/instr-dom-tech-33350018_1.out`
- `/home/anangia/moltbook/instr-dom-tech-33366494_1.err`
- `/home/anangia/moltbook/instr-dom-tech-33366494_1.out`
- `/home/anangia/moltbook/instr-mag0-32912086_1.err`
- `/home/anangia/moltbook/instr-mag0-32912086_1.out`
- `/home/anangia/moltbook/instr-mag0-32913087_1.err`
- `/home/anangia/moltbook/instr-mag0-32913087_1.out`
- `/home/anangia/moltbook/instr-mag0-32990461_1.err`
- `/home/anangia/moltbook/instr-mag0-32990461_1.out`
- `/home/anangia/moltbook/instr-mag0-33350013_1.err`
- `/home/anangia/moltbook/instr-mag0-33350013_1.out`
- `/home/anangia/moltbook/instr-mag0-33366489_1.err`
- `/home/anangia/moltbook/instr-mag0-33366489_1.out`
- `/home/anangia/moltbook/instr-mag0-33369470_1.err`
- `/home/anangia/moltbook/instr-mag0-33369470_1.out`
- `/home/anangia/moltbook/instr-mag1-32912087_1.err`
- `/home/anangia/moltbook/instr-mag1-32912087_1.out`
- `/home/anangia/moltbook/instr-mag1-32913088_1.err`
- `/home/anangia/moltbook/instr-mag1-32913088_1.out`
- `/home/anangia/moltbook/instr-mag1-32990462_1.err`
- `/home/anangia/moltbook/instr-mag1-32990462_1.out`
- `/home/anangia/moltbook/instr-mag1-33350014_1.err`
- `/home/anangia/moltbook/instr-mag1-33350014_1.out`
- `/home/anangia/moltbook/instr-mag1-33366490_1.err`
- `/home/anangia/moltbook/instr-mag1-33366490_1.out`
- `/home/anangia/moltbook/instr-mag25-32912089_1.err`
- `/home/anangia/moltbook/instr-mag25-32912089_1.out`
- `/home/anangia/moltbook/instr-mag25-32913090_1.err`
- `/home/anangia/moltbook/instr-mag25-32913090_1.out`
- `/home/anangia/moltbook/instr-mag25-32990464_1.err`
- `/home/anangia/moltbook/instr-mag25-32990464_1.out`
- `/home/anangia/moltbook/instr-mag25-33350016_1.err`
- `/home/anangia/moltbook/instr-mag25-33350016_1.out`
- `/home/anangia/moltbook/instr-mag25-33366492_1.err`
- `/home/anangia/moltbook/instr-mag25-33366492_1.out`
- `/home/anangia/moltbook/instr-mag5-32912088_1.err`
- `/home/anangia/moltbook/instr-mag5-32912088_1.out`
- `/home/anangia/moltbook/instr-mag5-32913089_1.err`
- `/home/anangia/moltbook/instr-mag5-32913089_1.out`
- `/home/anangia/moltbook/instr-mag5-32990463_1.err`
- `/home/anangia/moltbook/instr-mag5-32990463_1.out`
- `/home/anangia/moltbook/instr-mag5-33350015_1.err`
- `/home/anangia/moltbook/instr-mag5-33350015_1.out`
- `/home/anangia/moltbook/instr-mag5-33366491_1.err`
- `/home/anangia/moltbook/instr-mag5-33366491_1.out`
- `/home/anangia/moltbook/instr-mag5-33368242_5.err`
- `/home/anangia/moltbook/instr-mag5-33368242_5.out`
- `/home/anangia/moltbook/instr-mag5-33368243_1.err`
- `/home/anangia/moltbook/instr-mag5-33368243_1.out`
- `/home/anangia/moltbook/instr-mag5-33368244_2.err`
- `/home/anangia/moltbook/instr-mag5-33368244_2.out`
- `/home/anangia/moltbook/instr-mag5-33368245_3.err`
- `/home/anangia/moltbook/instr-mag5-33368245_3.out`
- `/home/anangia/moltbook/instr-mag5-33368246_4.err`
- `/home/anangia/moltbook/instr-mag5-33368246_4.out`
- `/home/anangia/moltbook/instr-mag5-33373106_1.err`
- `/home/anangia/moltbook/instr-mag5-33373106_1.out`
- `/home/anangia/moltbook/instr-val-33348966_1.err`
- `/home/anangia/moltbook/instr-val-33348966_1.out`
- `/home/anangia/moltbook/instr-val-33365119_1.err`
- `/home/anangia/moltbook/instr-val-33365119_1.out`

Check: reruns, emergency exports, final successful runs, and whether any condition still needs manual reconciliation.

## 11. Highest-priority manual review set

If you cannot read everything first, start with these:

- `/home/anangia/moltbook/analysis/olmo-base-vs-instruct-run-review.md`
- `/home/anangia/moltbook/alliance/slurm-experiment.sh`
- `/home/anangia/moltbook/content-gen-service/prompt-builder.js`
- `/home/anangia/moltbook/content-gen-service/together-client.js`
- `/home/anangia/moltbook/modal/serve_olmo3_base.py`
- `/home/anangia/moltbook/modal/serve_olmo3_instruct.py`
- `/home/anangia/moltbook/scripts/verify-base-model-integrity.py`
- `/home/anangia/moltbook/scripts/analyze-temporal-diversity.py`
- `/home/anangia/moltbook/scripts/analyze-shannon-entropy.py`
- `/home/anangia/moltbook/base-mag0-33351491_1.out`
- `/home/anangia/moltbook/base-mag5-33367324_1.out`
- `/home/anangia/moltbook/instr-mag0-33366489_1.out`
- `/home/anangia/moltbook/instr-dom-agi-33350017_1.out`
- `/home/anangia/moltbook/analysis/olmo-temporal-diversity.json`
- `/home/anangia/moltbook/analysis/olmo-shannon-entropy-3gram.json`
- `/home/anangia/moltbook/analysis/olmo-shannon-entropy-5gram.json`

## 12. What you need to verify manually

- Which run directories are the real final artifacts for each condition
- Whether the latest complete `2026-04-08` runs were actually used in analysis
- Whether instruct runs used `chat` mode or `completions` mode
- Whether metadata labels confuse orchestrator model with content model
- How much filtering, truncation, and rejection in the content-gen wrapper shaped results
- Which failed or partial runs should be ignored in any report
