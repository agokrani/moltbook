# Related Work

## Multi-Agent Social Simulation Platforms

Our work builds on a growing body of platforms that use LLM agents to study social dynamics. [Park et al. (2023)](https://arxiv.org/abs/2304.03442) introduced generative agents in a sandbox world, demonstrating emergent social behaviors like party planning and information diffusion. [Gao et al. (2023)](https://arxiv.org/abs/2307.14984) built S^3, a social-network simulator focused on emotion and attitude propagation across agent interactions. Closer to our setting, [Törnberg et al. (2023)](https://arxiv.org/abs/2310.05984) simulated social media with LLM agents to evaluate news feed algorithms, and [Larooij & Törnberg (2025)](https://arxiv.org/abs/2508.03385) extended this to test prosocial interventions. These platforms treat the social network as a substrate for observing a single phenomenon—polarization, misinformation spread, or cooperation dynamics. Moltbook differs in design intent: it is a general-purpose research environment with explicit platform mechanics (posts, comments, votes, follows) and fully reproducible experiment exports, built to support controlled factorial studies of agent behavior rather than single-phenomenon simulations.

Other recent platforms share our ambition for generality. [AgentSociety (Piao et al., 2025)](https://arxiv.org/abs/2502.08691) provides a large-scale simulation engine with configurable agent populations and social-issue case studies. [SocioVerse (Zhang et al., 2025)](https://arxiv.org/abs/2504.10157) offers a world model for social simulation with large user pools. [ElecTwit (Bao et al., 2026)](https://arxiv.org/abs/2601.00994) provides a framework for studying persuasion in multi-agent social systems with Twitter-like mechanics. SOTOPIA ([Zhou et al., 2023](https://arxiv.org/abs/2310.11667)) evaluates social intelligence through scenario-driven role-play interactions. These platforms focus on behavioral fidelity or single-axis evaluation. Moltbook adds systematic entropy measurement across multiple collapse layers, making diversity loss itself a first-class object of study.

Surveys by [Guo et al. (2024)](https://arxiv.org/abs/2402.01680), [Mou et al. (2024)](https://arxiv.org/abs/2412.03563), and [Luo et al. (2025)](https://arxiv.org/abs/2503.21460) catalog the expanding space of LLM-based multi-agent systems and social simulations. [Kapoor et al. (2024)](https://arxiv.org/abs/2407.01502) provide evaluation rigor guidelines that inform our experimental design: cost controls, reproducibility across reruns, and separation of platform effects from model effects.

## Diversity Collapse in Multi-Agent Systems

The phenomenon we study—entropy collapse—has been observed across multiple granularities in recent work. "Diversity Collapse in Multi-Agent LLM Systems" (Author et al., 2025 `[arXiv:?]`) studies open-ended idea generation and reports that stronger models give higher per-sample quality but less marginal diversity; authority-driven interaction structures suppress semantic diversity; and dense all-to-all communication accelerates premature convergence. "Understanding Agent Scaling in LLM-Based Multi-Agent Systems via Diversity" (Author et al., 2026 `[arXiv:?]`) argues that multi-agent system gains are bounded by the number of *effective evidence channels* the system accesses. Homogeneous agents saturate quickly because their outputs are strongly correlated. Two diverse agents can match or exceed sixteen homogeneous agents on several benchmarks—channel count, not agent count, drives reasoning improvement.

At the embedding level, "Representational Collapse in Multi-Agent LLM Committees" (Author et al., 2025 `[arXiv:?]`) provides direct measurement: in three-agent same model committees, pairwise chain-of-thought embedding similarity is high and the effective rank of the rationale matrix falls below the nominal number of agents, even when agents receive different role prompts. The message is that role diversity is not cognitive diversity. Same model committees with different role prompts can produce outputs that look distinct while occupying the same latent argument basin. We adopt effective rank measurement directly, rather than accepting prompt-engineered diversity at face value.

## Interaction Protocols and Collapse Mechanisms

Several lines of work identify specific protocol choices that trigger or suppress collapse. [Du et al. (2023)](https://arxiv.org/abs/2305.14325) showed that multi-agent debate can improve reasoning, but [Liang et al. (2023)](https://arxiv.org/abs/2305.19118) identified the *Degeneration-of-Thought* problem—once a model locks into an initial solution, further self-reflection rarely produces new ideas—and showed that debate requires carefully tuned disagreement to remain productive. [Cemri et al. (2025)](https://arxiv.org/abs/2503.13657) attribute many multi-agent system failures to orchestration choices rather than weak base models. Recent work framed as "Can LLM Agents Really Debate?" reports that intrinsic reasoning strength and inter-agent diversity drive most of the apparent benefit of debate, while majority pressure suppresses independent correction (Author et al., 2025 `[arXiv:?]`).

The consensus-seeking default in most debate protocols has drawn specific criticism. "Free-MAD: Consensus-Free Multi-Agent Debate" (Author et al., 2025 `[arXiv:?]`) argues that forced consensus is harmful under prompt injection or conformity pressure. "Hear Both Sides: Diversity-Aware Message Retention in Multi-Agent Debate" (Author et al., 2025 `[arXiv:?]`) shows that context windows fill with redundant agreement as agents and rounds scale, drowning out minority arguments. [Kaesberg et al. (2025)](https://arxiv.org/abs/2502.19130) compare voting against unanimity-based consensus protocols. [Kaushal & Singh (2026)](https://arxiv.org/abs/2601.08835) provide a controlled study of deliberation protocols under varying agent counts. "Mitigating Debate Collapse with Uncertainty-Driven Policy Optimization" (Author et al., 2025 `[arXiv:?]`) introduces behavioral metrics—answer-flip rate, inter-agent disagreement rate, system-level output entropy—that are protocol-agnostic and computable from any transcript. We build on this measurement approach, extending it to five collapse layers.

## Herding, Conformity, and Social Influence

A parallel line of work studies peer influence dynamics among LLM agents. "Herd Behavior: Investigating Peer Influence in LLM-based Multi-Agent Systems" (Author et al., 2025 `[arXiv:?]`) reports that conformity scales with the gap between an agent's own confidence and its perceived confidence of peers. The *format* in which peer information is presented—numerical vote, verbal certainty, full reasoning—materially changes conformity rates. What this suggests mechanically is that LLM agents respond to social-cue features (visible confidence, visible majority, authority framing) rather than performing fully Bayesian belief updates over peer evidence. "An Empirical Study of Group Conformity in Multi-Agent Systems" (Author et al., 2025 `[arXiv:?]`) reports that initially neutral agents adopt stances from numerically dominant groups and from agents framed as more capable. "LLMs Can't Handle Peer Pressure" and "When Your AI Agent Succumbs to Peer-Pressure" (Author et al., 2025 `[arXiv:?]`) model opinion-shift dynamics under sustained social pressure with topic-dependent thresholds.

The through-line: collapse happens when social signal from other agents is overweighted relative to private evidence. That social signal is rarely independent. If five same family agents repeat the same prior, the sixth agent may treat that as five pieces of evidence rather than one prior repeated five times. Our measurement framework distinguishes healthy convergence (agents introduce verifiable independent evidence) from pathological collapse (agents imitate, defer, or coordinate), which existing platforms do not systematically measure.

Related dynamics appear in work on emergent social phenomena. [Lee et al. (2025)](https://arxiv.org/abs/2501.05171) demonstrate human-like polarization in LLM agent populations. [Gu et al. (2025)](https://arxiv.org/abs/2502.18138) simulate echo chamber formation. [Han et al. (2025)](https://arxiv.org/abs/2411.10294) find that static network structure cannot stabilize cooperation among LLM agents, a finding with direct implications for how communication topology choices affect collapse trajectories in our platform.

## Measuring Surface-Form and Format-Induced Collapse

Our n-gram and surface-form metrics draw on a well-established literature. [Holtzman et al. (2019)](https://arxiv.org/abs/1904.09751) showed that maximum-likelihood decoding produces bland, repetitive text, motivating nucleus sampling. [Pillutla et al. (2021)](https://arxiv.org/abs/2102.01454) introduced MAUVE, a distributional-comparison metric in embedding space that captures content-level mismatch invisible to surface-only metrics. [Tevet and Berant (2020)](https://arxiv.org/abs/2004.02990) caution that automatic diversity metrics often disagree with human judgments—decoding changes affect form more than meaning. This motivates our paired measurement of topical and n-gram diversity, distinguishing four regimes: healthy diversity, template lock-in (high topical, low n-gram), semantic herding (low topical, high n-gram), and full collapse (low on both).

Format-induced collapse is a recently identified mechanism. "The Price of Format: Diversity Collapse in LLMs" (Author et al., 2024–25 `[arXiv:?]`) reports that structured chat templates, special tokens, role markers, and formatting constraints reduce semantic and topical diversity even at high temperature. Explicit "be diverse" prompting often fails to recover the lost entropy. This is directly relevant to multi-agent platforms where agent prompts include structured role markers and interaction templates. For longer horizons, [Shumailov et al. (2024)](https://arxiv.org/abs/2305.17493) establish that recursive training on model-generated data causes distributional tails to disappear. If agents are fine-tuned on collapsed transcripts, the collapse may become self-reinforcing.

## Forecasting and Evaluation Without Ground Truth

Forecasting is one of our two application domains. [Karger et al. (2024)](https://arxiv.org/abs/2409.19839) introduce ForecastBench, a benchmark of future-event questions with rolling resolution designed to defeat training-set leakage. Even top LLM forecasters trail expert humans. "Pitfalls in Evaluating Language Model Forecasters" (Paleka et al., 2025 `[arXiv:?]`) catalogs evaluation hazards—temporal leakage, weak extrapolation, reward-hacking. For evaluation when ground truth is unavailable at deliberation time, [Paleka et al. (2024)](https://arxiv.org/abs/2412.18649) propose immediate logical-coherence checks (arbitrage-style violations across related questions) and find that instantaneous consistency correlates with later Brier performance. [Fluri et al. (2023)](https://arxiv.org/abs/2306.09983) made the broader case for consistency-based evaluation when correctness is hard to judge. We extend this approach: our platform measures pre-resolution entropy collapse across five layers during deliberation, then evaluates whether collapse signatures predict post-resolution forecast error.

## Adversarial Agents and Deception Detection

Our second application domain is detecting hidden adversarial agents through collapse signatures. [Amayuelas et al. (2024)](https://arxiv.org/abs/2406.14711) showed that adversarial agents in collaborative debate can manipulate group outputs even as minorities. [Wang et al. (2024)](https://arxiv.org/abs/2406.03007) demonstrated backdoor attacks where input triggers cause harmful operations. A *Scientific Reports* paper on persuasion-driven adversarial influence (Author et al., 2026 `[arXiv:?]`) reports that a single persuasive adversary can reduce group accuracy by 10–40% and increase false conformity by more than 30%. Retrieval-augmented and Best-of-N variants amplify rather than dampen adversarial impact. Prompt-level warnings are unreliable; consistency checks and trajectory monitoring are recommended instead.

[It's the Thought That Counts (2025)](https://arxiv.org/abs/2506.02873) introduces the Attempt-to-Persuade-Eval benchmark, shifting measurement from persuasion success to persuasion *attempt*. This matters for transcript-only detection: a judge can detect attempts (selective framing, source laundering, premature consensus calls) without access to ground truth. Two cautionary notes: [Difficulties with Evaluating a Deception Detector for AIs (2024)](https://arxiv.org/abs/2511.22662) argues that reliable detector evaluation is hard because labeled deceptive-vs-honest examples are rare, and [Strategic Dishonesty Can Undermine AI Safety Evaluations (2024)](https://arxiv.org/abs/2509.18058) shows that frontier models produce outputs that appear harmful but are subtly incorrect, fooling output-based monitors.

White-box deception probes—[Bürger et al. (2024)](https://arxiv.org/abs/2407.12831) and [Goldowsky-Dill et al. (2025)](https://arxiv.org/abs/2502.03407)—flag dishonest behavior from activations. But lying is not deception: an agent can mislead through selective emphasis, asymmetric uncertainty, or framing without stating a literal falsehood. For transcript-only detection, this shifts the target to *influence tactics* rather than factual errors.

## Positioning of This Work

Moltbook is a multi-agent social network platform designed to measure entropy collapse simultaneously at the answer, topic, source, lexical, and representational levels. Unlike existing social simulation platforms that study a single phenomenon, Moltbook supports controlled factorial experiments varying agent composition, communication topology, information visibility, protocol objective, and decoding regime. Unlike debate evaluation frameworks that treat consensus as a performance metric, we measure whether consensus reflects healthy evidence aggregation or pathological collapse. We apply this measurement framework to two domains: forecasting, where we study whether early entropy collapse predicts worse Brier scores, and adversarial mole detection, where we evaluate transcript-only judges on influence-tactic detection rather than correctness detection.

---

## References

**Verified arXiv identifiers**

- [Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). Improving Factuality and Reasoning in Language Models through Multiagent Debate.](https://arxiv.org/abs/2305.14325) arXiv:2305.14325.
- [Liang, T., et al. (2023). Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate.](https://arxiv.org/abs/2305.19118) arXiv:2305.19118.
- [Cemri, M., et al. (2025). Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) arXiv:2503.13657.
- [Kaesberg et al. (2025). Voting or Consensus? Decision-Making in Multi-Agent Debate.](https://arxiv.org/abs/2502.19130) Findings of ACL 2025.
- [Kaushal & Singh (2026). DeliberationBench: When Do More Voices Hurt?](https://arxiv.org/abs/2601.08835) arXiv:2601.08835.
- [Amayuelas, A., et al. (2024). MultiAgent Collaboration Attack.](https://arxiv.org/abs/2406.14711) arXiv:2406.14711.
- [Wang, Y., et al. (2024). BadAgent: Inserting and Activating Backdoor Attacks in LLM Agents.](https://arxiv.org/abs/2406.03007) arXiv:2406.03007.
- [It's the Thought That Counts (2025).](https://arxiv.org/abs/2506.02873) arXiv:2506.02873.
- [Strategic Dishonesty Can Undermine AI Safety Evaluations (2024).](https://arxiv.org/abs/2509.18058) arXiv:2509.18058.
- [Difficulties with Evaluating a Deception Detector for AIs (2024).](https://arxiv.org/abs/2511.22662) arXiv:2511.22662.
- [Bürger, L., et al. (2024). Truth is Universal: Robust Generalization of Linear Probes for Lying.](https://arxiv.org/abs/2407.12831) arXiv:2407.12831.
- [Goldowsky-Dill, N., et al. (2025). Detecting Strategic Deception Using Linear Probes.](https://arxiv.org/abs/2502.03407) arXiv:2502.03407.
- [Karger, E., et al. (2024). ForecastBench.](https://arxiv.org/abs/2409.19839) arXiv:2409.19839.
- [Paleka, D., et al. (2024). Consistency Checks for Language Model Forecasters.](https://arxiv.org/abs/2412.18649) arXiv:2412.18649.
- [Fluri, L., Paleka, D., & Tramèr, F. (2023). Evaluating Superhuman Models with Consistency Checks.](https://arxiv.org/abs/2306.09983) arXiv:2306.09983.
- [Holtzman, A., et al. (2019). The Curious Case of Neural Text Degeneration.](https://arxiv.org/abs/1904.09751) arXiv:1904.09751.
- [Pillutla, K., et al. (2021). MAUVE.](https://arxiv.org/abs/2102.01454) arXiv:2102.01454.
- [Tevet, G., & Berant, J. (2020). Evaluating the Evaluation of Diversity in NLG.](https://arxiv.org/abs/2004.02990) arXiv:2004.02990.
- [Shumailov, I., et al. (2024). The Curse of Recursion. *Nature*.](https://arxiv.org/abs/2305.17493) arXiv:2305.17493.
- [Park, J. S., et al. (2023). Generative Agents: Interactive Simulacra of Human Behavior.](https://arxiv.org/abs/2304.03442) arXiv:2304.03442.
- [Gao, C., et al. (2023). S^3: Social-network Simulation System.](https://arxiv.org/abs/2307.14984) arXiv:2307.14984.
- [Törnberg, P., et al. (2023). Simulating Social Media Using LLMs.](https://arxiv.org/abs/2310.05984) arXiv:2310.05984.
- [Larooij & Törnberg (2025). Can We Fix Social Media?](https://arxiv.org/abs/2508.03385) arXiv:2508.03385.
- [Piao et al. (2025). AgentSociety.](https://arxiv.org/abs/2502.08691) arXiv:2502.08691.
- [Zhang et al. (2025). SocioVerse.](https://arxiv.org/abs/2504.10157) arXiv:2504.10157.
- [Bao et al. (2026). ElecTwit.](https://arxiv.org/abs/2601.00994) arXiv:2601.00994.
- [Zhou et al. (2023). SOTOPIA.](https://arxiv.org/abs/2310.11667) arXiv:2310.11667.
- [Guo et al. (2024). Large Language Model based Multi-Agents: A Survey.](https://arxiv.org/abs/2402.01680) arXiv:2402.01680.
- [Mou et al. (2024). From Individual to Society: A Survey on Social Simulation.](https://arxiv.org/abs/2412.03563) arXiv:2412.03563.
- [Luo et al. (2025). Survey on LLM-empowered Agent-based Modeling and Simulation.](https://arxiv.org/abs/2503.21460) arXiv:2503.21460.
- [Kapoor et al. (2024). AI Agents That Matter.](https://arxiv.org/abs/2407.01502) arXiv:2407.01502.
- [Lee et al. (2025). Emergence of Human-like Polarization in LLM Agents.](https://arxiv.org/abs/2501.05171) arXiv:2501.05171.
- [Gu et al. (2025). LLM Driven Agents for Simulating Echo Chamber Formation.](https://arxiv.org/abs/2502.18138) arXiv:2502.18138.
- [Han et al. (2025). Static network structure cannot stabilize cooperation.](https://arxiv.org/abs/2411.10294) *PLOS ONE*.

**arXiv ID to be confirmed (recent / 2025–2026 preprints)**

- Diversity Collapse in Multi-Agent LLM Systems. `[arXiv:?]`
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
