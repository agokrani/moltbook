# Appendix X. First-hour text counts for base-model writer runs

This appendix reports accepted non-seed agent-generated texts in the first 60 minutes for the standard single-model runs and the base-model writer runs discussed in the intervention section.

Base-model writer runs use an instruction-tuned controller to operate Moltbook. The base model generates post/comment text. Outputs modified by the controller before posting are rejected to preserve base-model authorship, so these runs can contain fewer accepted texts.

## Counts by condition

The table below counts first-hour non-seed posts. GLM-5 has fewer posts than GPT-5, Gemini Flash Lite, and Kimi K2.5 because GLM-5 produces many more comments/replies. The base-model writer runs have fewer accepted posts for a different reason: the controller/writer design rejects outputs modified by the controller to preserve base-model authorship.

| Condition | GPT-5 | Gemini Flash Lite | Kimi K2.5 | GLM-5 | Qwen Base writer | OLMo Base writer | OLMo Instruct writer |
|---|---:|---:|---:|---:|---:|---:|---:|
| Empty feed | 480 | 472 | 487 | 317 | 211 | 382 | 297 |
| 1 conspiracy seed | 508 | 345 | 455 | 266 | 249 | 227 | 470 |
| 5 conspiracy seeds | 282 | 423 | 469 | 228 | 154 | 249 | 459 |
| 25 conspiracy seeds | 346 | 418 | 480 | 251 | 270 | 225 | 351 |
| 25 AGI seeds | 464 | 396 | 444 | 245 | 277 | 212 | 284 |
| 25 tech seeds | 501 | 331 | 456 | 253 | 272 | 290 | 258 |

## Summary by writer setup

| Writer setup | Runs | Min | Median | Max | Mean |
|---|---:|---:|---:|---:|---:|
| GPT-5 | 6 | 282 | 472 | 508 | 430.2 |
| Gemini Flash Lite | 6 | 331 | 407 | 472 | 397.5 |
| Kimi K2.5 | 6 | 444 | 462 | 487 | 465.2 |
| GLM-5 | 6 | 228 | 252 | 317 | 260.0 |
| Qwen Base writer | 6 | 154 | 260 | 277 | 238.8 |
| OLMo Base writer | 6 | 212 | 238 | 382 | 264.2 |
| OLMo Instruct writer | 6 | 258 | 324 | 470 | 353.2 |
