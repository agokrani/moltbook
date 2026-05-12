# Intervention section draft

Status: standalone draft for targeted editing. This is not yet pasted into the paper.

Goal: replace the current thin framing (“Do intervention probes remove collapse?”) with a section that explains the hypotheses, the implementation details, and the result pattern.

## Can We Engineer Feed Diversity?

If agent feeds narrow over time, the next question is where the loop can be interrupted. We test three hypotheses: diversity might be restored by mixing different model families in a single run, by using base models to generate post and comment content, or by giving agents stronger persistent agendas. These experiments intervene at three points in the loop: the model population, the content-generation step, and the goals agents carry across heartbeats.

### Can Mixing Models Preserve Feed Diversity?

The motivation for this experiment comes directly from the canonical runs. Different model families did not converge on the same repeated phrases: GPT-5, Gemini Flash Lite, Kimi K2.5, and GLM-5 each produced different 5-grams, templates, and recurring frames. If those differences come from training data, post-training, decoding behavior, or model-specific response style, then mixing model families inside a single run should increase the diversity of the feed. The expectation is that model-level variation would become feed-level variation: different model families would contribute different phrasings, templates, and frames, making it harder for any one style to dominate.

Mixing models does not preserve open-ended feed diversity. Across all six seed conditions, the mixed-model runs move in the direction of collapse, on all three core metrics: Distinct-5 decreases, gzip ratio decreases, and LLM collapse index increases.

**Table X. Mixed models still narrow across all seed conditions.** Values show change from cumulative 0–15m to cumulative 0–60m. Collapse direction is Δ Distinct-5 < 0, Δ gzip < 0, and Δ LLM collapse > 0.

| Condition | GPT-5 Δ D-5 | GPT-5 Δ gzip | GPT-5 Δ LLM | Gemini Δ D-5 | Gemini Δ gzip | Gemini Δ LLM | Mixed Δ D-5 | Mixed Δ gzip | Mixed Δ LLM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Empty feed | -0.019 | -0.049 | +0.16 | -0.024 | -0.038 | +0.05 | -0.037 | -0.013 | +0.30 |
| 1 conspiracy seed | -0.061 | -0.048 | +0.06 | -0.024 | -0.035 | +0.15 | -0.029 | -0.030 | +0.39 |
| 5 conspiracy seeds | -0.116 | -0.055 | +0.17 | -0.228 | -0.096 | +0.34 | -0.060 | -0.029 | +0.31 |
| 25 conspiracy seeds | -0.115 | -0.048 | +0.15 | -0.031 | -0.036 | +0.19 | -0.075 | -0.030 | +0.31 |
| 25 AGI seeds | -0.157 | -0.058 | +0.16 | -0.018 | -0.032 | +0.10 | -0.074 | -0.036 | +0.21 |
| 25 tech seeds | -0.199 | -0.075 | +0.26 | -0.023 | -0.032 | +0.11 | -0.082 | -0.027 | +0.22 |

Compared with GPT-5 and Gemini Flash Lite, the mixed-model runs often have smaller drops in Distinct-5 and gzip, especially gzip. But this does not mean the feed remains diverse. The LLM collapse index rises in every mixed-model condition, and in five of six conditions it rises more than in either GPT-5 or Gemini. Mixing models therefore weakens some surface redundancy signals, while the LLM judge still sees increasing repetition, rigidity, and frame convergence.

Shared phrase adoption is also weaker than in single-model runs, but it does not disappear: the top exact phrase reaches at least half the agents in 4/6 mixed-model runs, compared with 24/24 single-model runs. Model diversity therefore changes how repetition spreads, but the shared feed can still synchronize agents around repeated phrases and frames.

### Can Base Models Restore Text Diversity?

The second hypothesis targets the model that writes the text. A possible explanation for repeated phrases and templates is that instruction-tuned or RLHF-trained agents are optimized to be helpful, compliant, and easy to follow. That post-training can make responses more standardized: agents may converge on checklist formats, polite framing, safety caveats, or assistant-like turns of phrase. This concern is consistent with prior work showing that decoding, formatting, and prompt structure affect linguistic diversity, and with work on diversity collapse in aligned multi-agent systems \citep{li2016diversity,zhu2018selfbleu,holtzman2020curious,tevet2021evaluating,yun2025format,chen2026diversitycollapse}. If instruction-tuned writing is part of the problem, then base models should help because they have not been tuned as strongly toward instruction-following behavior.

We could not simply replace the whole agent with a base model. Operating Moltbook requires following the heartbeat, deciding whether to post or comment, using API tools, and maintaining the action loop. Base models were unreliable at this control layer. We therefore used a split design: an instruction-tuned controller operated the agent and chose the action, while a base model generated the post or comment text. In other words, the controller decided what to do, and the base model wrote what to say. To preserve the interpretation of the run as base-authored content, we rejected outputs when the controller modified the base model’s text before posting. Further implementation details are described in Appendix Y.

This acceptance rule affects how the result should be read. The base-model runs contain fewer accepted agent-generated texts. The runs with GPT-5 and Gemini Flash Lite produce median counts of 472 and 407, respectively. Qwen Base and OLMo Base produce 260 and 238 accepted texts. That difference matters: fewer accepted texts create fewer chances for an exact 5-gram to recur, and cumulative Distinct-5 can look higher even when the feed is not genuinely more diverse. For that reason, higher Distinct-5 in these runs is not enough by itself to show that base models restored diversity. Detailed post counts for the standard and base-model runs are reported in Appendix X.

Qwen Base weakens lexical repetition; OLMo Base does not. Qwen Base is the strongest evidence for the base-model hypothesis: across six conditions, Distinct-5 is nearly flat, declining in only 3/6 conditions with a median change near zero. Its top exact 5-gram reaches at least half the agents in only 3/6 runs. But the other metrics still show feed collapse. Gzip still declines in 5/6 Qwen Base conditions, and the LLM collapse index rises in 4/6. In other words, exact phrase repetition weakens, while compression and the LLM judge still detect growing redundancy, repetition, rigidity, or frame convergence. OLMo Base points the other way. It declines on Distinct-5 in 6/6 conditions and on gzip and LLM collapse in 5/6, while its top exact 5-gram reaches at least half the agents in 6/6 runs. Replacing the writer with a base model can weaken one form of lexical repetition, but it does not reliably restore feed diversity.

**Table X. Base writers do not behave uniformly.** Values show change from cumulative 0–15m to cumulative 0–60m. Collapse direction is Δ Distinct-5 < 0, Δ gzip < 0, and Δ LLM collapse > 0.

| Condition | Qwen ΔD-5 | Qwen Δgzip | Qwen ΔLLM | OLMo Base ΔD-5 | OLMo Base Δgzip | OLMo Base ΔLLM |
|---|---:|---:|---:|---:|---:|---:|
| Empty feed | +0.001 | -0.003 | +0.21 | -0.002 | +0.005 | -0.05 |
| 1 conspiracy seed | -0.011 | -0.022 | -0.22 | -0.030 | -0.012 | +0.16 |
| 5 conspiracy seeds | +0.010 | -0.000 | -0.03 | -0.009 | -0.022 | +0.15 |
| 25 conspiracy seeds | -0.003 | -0.024 | +0.41 | -0.008 | -0.015 | +0.07 |
| 25 AGI seeds | -0.002 | +0.002 | +0.02 | -0.013 | -0.010 | +0.07 |
| 25 tech seeds | +0.012 | -0.008 | +0.10 | -0.030 | -0.034 | +0.20 |

Base-model writing is also not an easy engineering fix. The base model cannot run the agent loop by itself, so the system needs an instruction-tuned controller, a handoff to the base model for text generation, and an acceptance rule that rejects controller-rewritten drafts. That makes base-model writing useful as a diagnostic, but awkward as a permanent solution. A better direction may be to study how to preserve more text diversity inside instruction-tuned agents themselves: how pretraining behavior, next-token prediction, instruction tuning, and RL-style post-training interact to shape the diversity of the text agents produce.

### Do Agents with Private Goals Keep the Feed Diverse?

The third experiment approximates a feature of the original Moltbook setting. OpenClaw agents were not only social-media participants: they often had user goals, or ongoing projects, and Moltbook was something they used alongside those goals. This matters because the feed was not the only source of what an agent cared about next. An agent debugging a tool, tracking a forecast, or working through an interpretation question could enter Moltbook with a topic already in hand, rather than deriving its next post entirely from the posts it had just read. The intervention tests whether that kind of outside commitment makes agents less likely to copy the same phrases, templates, and frames from the shared feed.

We could not reproduce arbitrary user-assigned tasks in a controlled run, so we simulated this structure through the heartbeat. Each agent was assigned a stable private track: coding, hadith commentary, forecasting, fitness, or cinema. The heartbeat instructed agents to check in with that track before browsing Moltbook and to post about it. The goal was to test whether agents with a durable source of attention outside the shared feed would resist converging on the same repeated phrases.

The effect of giving agents private goals is that it reduces shared phrase adoption across agents. In GPT-5 runs, the top exact 5-gram reaches at least half the agents in 6/6 conditions. In runs with private goals, this happens in 0/9 runs, and the median top phrase reaches only 3 agents rather than 7. This suggests that outside commitments do interrupt one form of feed collapse: agents are less likely to all pick up the same phrase from the public feed.

But private goals do not remove repetition. They shift it from the group to the individual agent. In GPT-5 baseline runs, about 26% of the mentions of the top repeated 5-gram come from one agent. In runs with private goals, that share rises to about 67%. The top repeated phrase is therefore less likely to spread across many agents, but when it appears, it is often repeated by one agent. Private goals therefore reduce shared catchphrases, but they can leave individual agents repeating their own templates, questions, or frames.

The same pattern appears in the LLM collapse index. As Table X shows, runs with private goals still increase over time: all 8 GPT-5 runs with private goals have positive deltas. At the same time, the increase is smaller than the GPT-5 baseline in five of six seed conditions. Private goals therefore reduce the strength of feed-wide synchronization, but they do not keep the feed open-ended.

**Table X. Private goals reduce but do not eliminate increases in the LLM collapse index.**

| Condition | GPT-5 baseline Δ LLM | Private goals Δ LLM | Difference |
|---|---:|---:|---:|
| Empty feed | +0.241 | +0.110 | -0.131 |
| 1 conspiracy seed | +0.019 | +0.022 | +0.003 |
| 5 conspiracy seeds | +0.407 | +0.035 | -0.371 |
| 25 conspiracy seeds | +0.243 | +0.056 | -0.187 |
| 25 AGI seeds | +0.183 | +0.055 | -0.128 |
| 25 tech seeds | +0.374 | +0.117 | -0.257 |

Our setup held private goals fixed across the run. This matches one part of the Moltbook setting, where agents may carry user goals or ongoing projects into the feed. It does not cover another plausible setting, where users repeatedly update, replace, or redirect those goals over time. Such changes could introduce additional variation into the feed, and are an important direction for follow-up. Taken together, private goals make collapse less shared across agents, but they do not stop individual agents from settling into their own templates.

The overall result is that these interventions do not fail in the same way. Mixed-model runs preserve model-level heterogeneity but can still converge through the shared feed. Base-model content generation improves some lexical-diversity metrics but does not prevent rhetorical or semantic narrowing. Private goals reduce cross-agent phrase adoption but shift repetition toward agent-specific or track-specific repeated forms. Together, these experiments suggest that collapse is not only a property of one model class or one prompt format. It is a platform-level feedback effect: agents write the environment that future agents read.

---

## Methods paragraph draft: base-model-as-tool design

For base-model probes, we did not run the base model as the full autonomous agent. A Moltbook agent must follow heartbeat instructions, decide among platform actions, call API tools, and maintain the interaction loop. Base models were not reliable enough at this instruction-following and tool-use layer. We therefore separated **control** from **content generation**. An instruction-tuned controller read the feed and selected the next action. If the action required a post or comment, the controller invoked a base model as a generation tool, passing the relevant feed context and action request. The resulting text was then posted by the controller. These runs therefore test whether replacing the natural-language content generator with a base model increases feed diversity, not whether an unaided base model can operate Moltbook end-to-end.

---

## Shorter paper-ready version

We tested three natural anti-collapse hypotheses. First, **model heterogeneity**: because different model families develop different local attractors in the canonical runs, a mixed roster might increase aggregate diversity. It did not remove collapse. The top exact phrase still reached at least half the agents in 4/6 mixed-roster runs, and in the selected `mag25` comparison Distinct-5, gzip, and LLM collapse all moved in the collapse direction.

Second, **base-model content generation**: if collapse is partly caused by instruction tuning or RLHF-style assistant behavior, then base models might produce higher-entropy posts. Because base models could not reliably operate Moltbook directly, we used them only as content-generation tools: an instruction-tuned controller selected the action and called the base model to draft the post or comment. This improved some lexical metrics but did not remove attractors. In the selected Qwen-base-tool `mag25` run, Distinct-5 remained high, but gzip fell and LLM collapse rose; across base-model-as-tool runs, 15/18 still had a top phrase adopted by at least half the agents.

Third, **persistent private agendas**: if agents converge because they over-adapt to the shared public feed, stronger persistent goals might preserve individuality. Obsession prompting reduced cross-agent phrase adoption: 0/9 runs had a top phrase reaching half the agents. But repetition became more concentrated within fewer agents, and LLM collapse still rose in the selected comparison. The intervention changed the failure mode rather than eliminating it.

Overall, the probes suggest that collapse is not just a homogeneous-model artifact, not simply an RLHF artifact, and not fully solved by stronger agent-level agendas. The shared feed remains a synchronization mechanism.

---

## Evidence to cite in this section

### Phrase-adoption scorecard

Source:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step08_intervention_probe_llm/intervention_phrase_adoption_summary.csv
```

Key numbers:

| Cohort | Runs | Top phrase reaches >= half agents | Median top-phrase agents | Median top-agent share |
|---|---:|---:|---:|---:|
| Canonical homogeneous | 24 | 24 | 7.5 | 0.279 |
| Base model as tool | 18 | 15 | 8.0 | 0.231 |
| Mixed-model roster | 6 | 4 | 5.0 | 0.410 |
| Obsession prompting | 9 | 0 | 3.0 | 0.667 |

Interpretation:

- Mixed rosters reduce but do not eliminate cross-agent phrase adoption.
- Base-model-as-tool runs still often produce shared phrase attractors.
- Obsession prompting reduces group-level adoption but concentrates repetition within fewer agents.

### Selected `mag25` comparison

Source:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step10_intervention_selected_single_runs/intervention_selected_single_runs_mag25_by_run.csv
```

Start-to-final values:

| Run | Distinct-5 | Gzip | LLM collapse |
|---|---:|---:|---:|
| Canonical GPT-5 | 0.930 -> 0.808 | 0.345 -> 0.291 | 4.43 -> 4.59 |
| Qwen base tool | 0.994 -> 0.985 | 0.370 -> 0.344 | 3.51 -> 3.94 |
| Mixed-model roster | 0.974 -> 0.899 | 0.338 -> 0.307 | 3.44 -> 3.75 |
| Obsession GPT-5 | 0.904 -> 0.904 | 0.370 -> 0.360 | 4.14 -> 4.18 |

Interpretation:

- Qwen base tool preserves more lexical diversity but still becomes more compressible and more collapsed by LLM judgment.
- Mixed roster still narrows over time.
- Obsession prompting flattens Distinct-5 but does not remove judged collapse.

---

## Open questions for targeted edits

1. What exactly is the third hypothesis wording? Is “persistent private agenda” accurate, or should we describe obsession prompting differently?
2. Which citation should support “instruction tuning/RLHF reduces diversity or entropy”? Need the strongest defensible reference.
3. Should this section include the selected `mag25` figure, the phrase-adoption scorecard, or both?
4. Do we want to include OLMo base/instruct details here, or keep them out of the main paper to avoid expanding the intervention section too much?
5. Should “base model as tool” be described in Results, Methods, or both? My recommendation: one short Results explanation plus the detailed control/content split in Methods.
