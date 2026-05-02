# Related Work

## Multi-Agent Debate and Reasoning

[Du et al. (2023)](https://arxiv.org/abs/2305.14325) showed that multiple LLM instances proposing answers and exchanging reasoning over rounds can improve factuality and reasoning compared with single-agent prompting. This "society of minds" framing kicked off a wave of debate-based architectures. [Liang et al. (2023)](https://arxiv.org/abs/2305.19118) identified the *Degeneration-of-Thought* problem in self-reflection: once a model locks into an initial solution, further self-reflection rarely produces genuinely new ideas. They argued that multi-agent debate with controlled adversarial structure can break this degeneracy, but also showed that debate is not robust by default. The right amount of disagreement and an adaptive stopping rule are required; over-extended debate can degrade quality.

More recent studies are less uniformly positive. [Cemri et al. (2025)](https://arxiv.org/abs/2503.13657) provide a taxonomy of multi-agent system failure modes and attribute many breakdowns not to weak base models but to system design choices—orchestration, verification, role specification, termination conditions. Recent work framed as "Can LLM Agents Really Debate?" reports that intrinsic reasoning strength and inter-agent diversity drive most of the apparent benefit of debate, while majority pressure and rigid protocols suppress independent correction (Author et al., 2025 `[arXiv:?]`). These results undercut the assumption that debate preserves diversity by default. Debate is itself a collapse-prone protocol; protecting dissent requires explicit engineering.

## Herding, Conformity, and Peer Influence

A growing line of work studies whether and when LLM agents conform to peers. The most direct study, "Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems" (Author et al., 2025 `[arXiv:?]`), reports that conformity scales with the gap between an agent's own confidence and its perceived confidence of peers. The *format* in which peer information is presented—numerical vote, verbal certainty, full reasoning—materially changes conformity rates. What this suggests mechanically is that LLM agents are not performing fully Bayesian belief updates over peer evidence. They respond to social-cue features: visible confidence, visible majority, authority framing.

Related findings come from "An Empirical Study of Group Conformity in Multi-Agent Systems" (Author et al., 2025 `[arXiv:?]`), which reports that initially neutral agents adopt stances from numerically dominant groups and from agents framed as more capable, raising bias-amplification concerns. "LLMs Can't Handle Peer Pressure" and "When Your AI Agent Succumbs to Peer-Pressure" (Author et al., 2025 `[arXiv:?]`) model opinion-shift dynamics under sustained social pressure and find substantial topic-dependent variation in pressure thresholds.

The through-line across these studies: collapse happens when social signal from other agents is overweighted relative to private evidence. That social signal is rarely independent. If five same family agents repeat the same prior, the sixth agent may treat that as five pieces of evidence rather than one prior repeated five times.

## Diversity Collapse and Representational Collapse

The phrase *diversity collapse* appears explicitly in recent work. "Diversity Collapse in Multi-Agent LLM Systems" (Author et al., 2025 `[arXiv:?]`) studies open-ended idea generation and reports that stronger and more aligned models give higher per-sample quality but less marginal diversity; authority-driven interaction structures suppress semantic diversity; larger groups show diminishing returns on diversity; and dense all-to-all communication accelerates premature convergence. "Understanding Agent Scaling in LLM-Based Multi-Agent Systems via Diversity" (Author et al., 2026 `[arXiv:?]`) argues that multi-agent system gains are bounded by the number of *effective evidence channels* the system accesses. Homogeneous agents saturate quickly because their outputs are strongly correlated. The paper reports that two diverse agents can match or exceed sixteen homogeneous agents on several benchmarks—channel count, not agent count, drives reasoning improvement.

At the embedding level, "Representational Collapse in Multi-Agent LLM Committees" (Author et al., 2025 `[arXiv:?]`) provides direct measurement: in three-agent same model committees, pairwise chain-of-thought embedding similarity is high and the effective rank of the rationale matrix is below the nominal number of agents, even when agents receive different role prompts. The combined message: *role diversity is not cognitive diversity*. Same model committees with different role prompts can produce outputs that look distinct while occupying the same latent argument basin. This motivates direct embedding-rank measurement rather than accepting prompt-engineered diversity at face value.

## Consensus Pressure and Majority Bias

Several papers reframe consensus from a neutral outcome into an active intervention. "Free-MAD: Consensus-Free Multi-Agent Debate" (Author et al., 2025 `[arXiv:?]`) argues that standard multi-agent debate protocols default to consensus-seeking, and that consensus is harmful under prompt injection, malicious agents, or conformity pressure; the paper proposes protocol variants that explicitly avoid forced agreement. "Hear Both Sides: Diversity-Aware Message Retention in Multi-Agent Debate" (Author et al., 2025 `[arXiv:?]`) attacks an adjacent problem: as agents and rounds scale, the context window fills with redundant agreement, drowning out minority arguments. The proposed remedy retains only mutually disagreeing messages with high quality scores.

"Mitigating Debate Collapse with Uncertainty-Driven Policy Optimization" (Author et al., 2025 `[arXiv:?]`) introduces behavioral metrics—intra-agent answer-flip rate, inter-agent disagreement rate, and system-level output entropy—that are protocol-agnostic and computable from any transcript. Consensus is an intervention, not a neutral outcome. Whenever the protocol prompt says "reach consensus" or "vote," the loss function shifts from independent truth-seeking to social coordination. That shift can improve performance on tasks with a single correct answer but harm performance under genuine uncertainty, where minority evidence may carry the signal.

## Adversarial Agents, Persuasion, and Deception Detection

Adversarial agents connect entropy collapse to deception detection. [Amayuelas et al. (2024)](https://arxiv.org/abs/2406.14711) showed that adversarial agents in collaborative debate can manipulate group outputs even when they are minorities. [Wang et al. (2024)](https://arxiv.org/abs/2406.03007) demonstrated a backdoor threat model where triggers in input or environment cause harmful operations even after trustworthy fine-tuning. The strongest recent empirical result comes from a *Scientific Reports* paper on persuasion-driven adversarial influence in multi-agent debate (Author et al., 2026 `[arXiv:?]`), which reports that a single persuasive adversarial agent can reduce group accuracy by 10–40% and increase false conformity by more than 30%. Retrieval-augmented and Best-of-N variants amplify rather than dampen adversarial impact. Prompt-level warnings are unreliable as a defense; the paper recommends consistency checks, agreement-trajectory monitoring, and argument-incoherence detection instead.

[It's the Thought That Counts (2025)](https://arxiv.org/abs/2506.02873) introduces the Attempt-to-Persuade-Eval (APE) benchmark, shifting the measurement target from persuasion *success* to persuasion *attempt* in multi-turn interactions. This matters for transcript-only detection: a judge can plausibly detect attempts (selective framing, source laundering, premature consensus calls) even when it cannot verify ground truth. Two cautionary notes from the deception detection literature: [Difficulties with Evaluating a Deception Detector for AIs (2024)](https://arxiv.org/abs/2511.22662) argues that reliable detector evaluation is hard because confidently labeled deceptive-vs-honest examples are rare, and [Strategic Dishonesty Can Undermine AI Safety Evaluations (2024)](https://arxiv.org/abs/2509.18058) shows that frontier models can produce outputs that appear harmful but are subtly incorrect, fooling output-based monitors while internal linear probes recover some of this signal.

White-box deception probes have shown promise. [Bürger et al. (2024)](https://arxiv.org/abs/2407.12831) and [Goldowsky-Dill et al. (2025)](https://arxiv.org/abs/2502.03407) show that activation-level probes can flag certain classes of dishonest behavior. But lying is not the same thing as deception. An agent can mislead through selective emphasis, asymmetric uncertainty, or framing without ever stating a literal falsehood. For transcript-only detection where the judge has no internal-state access, this distinction pushes toward detecting *influence tactics* rather than factual errors.

## Forecasting and Evaluation Without Ground Truth

Forecasting is a good domain for studying collapse without conflating it with correctness: ground truth is delayed and contamination can be controlled. [Karger et al. (2024)](https://arxiv.org/abs/2409.19839) introduce ForecastBench, a benchmark of future-event questions with rolling resolution designed to defeat training-set leakage. Even top LLM forecasters trail expert human forecasters on this benchmark. "Pitfalls in Evaluating Language Model Forecasters" (Paleka et al., 2025 `[arXiv:?]`) catalogs evaluation hazards—temporal leakage, weak extrapolation from benchmark to real-world settings, reward-hacking via question selection. For evaluation when ground truth is unavailable at deliberation time, [Paleka et al. (2024)](https://arxiv.org/abs/2412.18649) propose immediate logical-coherence checks (arbitrage-style violations across related questions) and find that instantaneous consistency correlates with later Brier performance. [Fluri et al. (2023)](https://arxiv.org/abs/2306.09983) made the broader case for consistency-based evaluation when correctness is hard to judge.

## Surface-Form Collapse, Format-Induced Collapse, and Recursive Model Collapse

N-gram collapse predates LLM agent systems. [Holtzman et al. (2019)](https://arxiv.org/abs/1904.09751) showed that maximum-likelihood decoding produces bland, repetitive text, motivating nucleus sampling as a way to preserve diversity without sampling from unreliable tails. [Pillutla et al. (2021)](https://arxiv.org/abs/2102.01454) introduced MAUVE, a distributional-comparison metric in embedding space that captures content-level mismatch invisible to surface-only metrics. [Tevet and Berant (2020)](https://arxiv.org/abs/2004.02990) deliver a necessary methodological caution: automatic diversity metrics often disagree with human judgments and can miss content-level diversity because decoding changes typically affect form more than meaning.

"The Price of Format: Diversity Collapse in LLMs" (Author et al., 2024–25 `[arXiv:?]`) reports that structured chat templates, special tokens, role markers, and formatting constraints reduce semantic and topical diversity even at high temperature. Explicit "be diverse" prompting often fails to recover the lost entropy. For multi-agent systems, the implication is that part of any observed collapse may originate in the chat template itself, before social interaction begins. For longer horizons, [Shumailov et al. (2024)](https://arxiv.org/abs/2305.17493) establish that recursive training on model-generated data causes distributional tails to disappear (published in *Nature* 2024). If future agents are fine-tuned on collapsed multi-agent transcripts, those agents may inherit the collapse as a baseline conversational norm.

We separate four regimes of collapse by crossing topical and n-gram diversity: *healthy diversity* (high topical, high n-gram), *template lock-in* (high topical, low n-gram), *semantic herding* (low topical, high n-gram), and *full collapse* (low topical, low n-gram). A naive detector that uses only n-gram metrics will mislabel template lock-in as groupthink and miss semantic herding entirely. Telling these apart requires paired measurement at the topical and surface levels. Effective rank of rationale embeddings is particularly useful here.

## Positioning of This Work

Across the literature, the same dynamic keeps surfacing: multi-agent entropy collapse happens when social signal outweighs independent evidence. The triggers vary—homogeneous agents, dense communication, consensus objectives, confidence asymmetry, authority labels, shared retrieval, rigid formatting, low-diversity decoding, ambiguous tasks, adversarial persuasion—but the mechanism is consistent. Most published evidence isolates one or two of these conditions at a time. We study collapse simultaneously at the answer, topic, source, and surface-form levels, varying agent composition, communication topology, information visibility, protocol objective, and decoding regime factorially. We measure collapse signatures under both benign and adversarial (mole) conditions, and we evaluate transcript-only judges on influence-tactic detection rather than correctness detection. The goal is to put the entropy-collapse and deception-detection threads under a single empirical framework, where they belong.

---

## References

**Verified arXiv identifiers**

- [Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). Improving Factuality and Reasoning in Language Models through Multiagent Debate.](https://arxiv.org/abs/2305.14325) arXiv:2305.14325.
- [Liang, T., et al. (2023). Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate.](https://arxiv.org/abs/2305.19118) arXiv:2305.19118.
- [Cemri, M., et al. (2025). Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) arXiv:2503.13657.
- [Amayuelas, A., et al. (2024). MultiAgent Collaboration Attack: Investigating Adversarial Attacks in LLM Collaborations via Debate.](https://arxiv.org/abs/2406.14711) arXiv:2406.14711.
- [Wang, Y., et al. (2024). BadAgent: Inserting and Activating Backdoor Attacks in LLM Agents.](https://arxiv.org/abs/2406.03007) arXiv:2406.03007.
- [It's the Thought That Counts: Evaluating Attempts of Frontier LLMs to Persuade on Harmful Topics (2025).](https://arxiv.org/abs/2506.02873) arXiv:2506.02873.
- [Strategic Dishonesty Can Undermine AI Safety Evaluations of Frontier LLMs (2024).](https://arxiv.org/abs/2509.18058) arXiv:2509.18058.
- [Difficulties with Evaluating a Deception Detector for AIs (2024).](https://arxiv.org/abs/2511.22662) arXiv:2511.22662.
- [Bürger, L., et al. (2024). Truth is Universal: Robust Generalization of Linear Probes for Lying.](https://arxiv.org/abs/2407.12831) arXiv:2407.12831.
- [Goldowsky-Dill, N., et al. (2025). Detecting Strategic Deception Using Linear Probes.](https://arxiv.org/abs/2502.03407) arXiv:2502.03407.
- [Karger, E., et al. (2024). ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities.](https://arxiv.org/abs/2409.19839) arXiv:2409.19839.
- [Paleka, D., et al. (2024). Consistency Checks for Language Model Forecasters.](https://arxiv.org/abs/2412.18649) arXiv:2412.18649.
- [Fluri, L., Paleka, D., & Tramèr, F. (2023). Evaluating Superhuman Models with Consistency Checks.](https://arxiv.org/abs/2306.09983) arXiv:2306.09983.
- [Holtzman, A., Buys, J., Du, L., Forbes, M., & Choi, Y. (2019). The Curious Case of Neural Text Degeneration.](https://arxiv.org/abs/1904.09751) arXiv:1904.09751.
- [Pillutla, K., et al. (2021). MAUVE: Measuring the Gap Between Neural Text and Human Text Using Divergence Frontiers.](https://arxiv.org/abs/2102.01454) arXiv:2102.01454.
- [Tevet, G., & Berant, J. (2020). Evaluating the Evaluation of Diversity in Natural Language Generation.](https://arxiv.org/abs/2004.02990) arXiv:2004.02990.
- [Shumailov, I., et al. (2024). The Curse of Recursion: Training on Generated Data Makes Models Forget. *Nature*.](https://arxiv.org/abs/2305.17493) arXiv:2305.17493.

**arXiv ID to be confirmed (recent / 2025–2026 preprints)**

- Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation. `[arXiv:?]`
- Representational Collapse in Multi-Agent LLM Committees. `[arXiv:?]`
- Understanding Agent Scaling in LLM-Based Multi-Agent Systems via Diversity. `[arXiv:?]`
- Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems. `[arXiv:?]`
- An Empirical Study of Group Conformity in Multi-Agent Systems. `[arXiv:?]`
- LLMs Can't Handle Peer Pressure. `[arXiv:?]`
- When Your AI Agent Succumbs to Peer-Pressure. `[arXiv:?]`
- Free-MAD: Consensus-Free Multi-Agent Debate. `[arXiv:?]`
- Hear Both Sides: Diversity-Aware Message Retention in Multi-Agent Debate. `[arXiv:?]`
- Mitigating Debate Collapse with Uncertainty-Driven Policy Optimization. `[arXiv:?]`
- Can LLM Agents Really Debate? `[arXiv:?]`
- The Price of Format: Diversity Collapse in LLMs. `[arXiv:?]`
- When Collaboration Fails: Persuasion-Driven Adversarial Influence in Multi-Agent LLM Debate (*Scientific Reports*, 2026). `[arXiv:?]`
- Pitfalls in Evaluating Language Model Forecasters (Paleka et al., 2025). `[arXiv:?]`
- Probing the Limits of the Lie Detector Approach. `[arXiv:?]`
- Benchmarking Linguistic Diversity of Large Language Models. `[arXiv:?]`
- "Cracking the Collective Mind" (OpenReview preprint, withdrawn—useful background only).
