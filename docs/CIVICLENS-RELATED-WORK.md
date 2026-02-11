# CivicLens: Related Work (Web Search Notes)

This doc is a curated (not exhaustive) set of papers/tools to help position **CivicLens** for an ACL/NeurIPS-style submission.

**Core positioning idea:** CivicLens is a *measurable social-network environment* for multi-agent LLMs (posts/comments/votes/follows + full activity logs + reproducible exports), with benchmarkable tasks like **consensus generation** and **protocol adoption**.

**Last updated:** 2026-02-11 (web search; arXiv/ACL links spot-checked).

---

## 2024–2026 High-Leverage Adds (fast path)

If you only read one section, read this one — it’s a shortlist of “directly relevant to CivicLens” work from **2024–2026**.

- **DeliberationBench: When Do More Voices Hurt? A Controlled Study of Multi-LLM Deliberation Protocols** (Kaushal & Singh, 2026).
  - https://arxiv.org/abs/2601.08835
- **Voting or Consensus? Decision-Making in Multi-Agent Debate** (Kaesberg et al., Findings of ACL 2025).
  - ACL: https://aclanthology.org/2025.findings-acl.606/
  - arXiv: https://arxiv.org/abs/2502.19130
- **Free-MAD: Consensus-Free Multi-Agent Debate** (Cui et al., 2025).
  - https://arxiv.org/abs/2509.11035
- **MultiAgentBench: Evaluating Multi-Agent in LLMs** (Wang et al., 2025).
  - https://arxiv.org/abs/2503.01935
- **AgentNet: Decentralized Evolutionary Coordination for LLM-based Multi-Agent Systems** (Yang et al., 2025).
  - https://arxiv.org/abs/2504.00587
- **ElecTwit: A Framework for Studying Persuasion in Multi-Agent Social Systems** (Bao et al., 2026).
  - https://arxiv.org/abs/2601.00994
- **Can We Fix Social Media? Testing Prosocial Interventions using Generative Social Simulation** (Larooij & Törnberg, 2025).
  - https://arxiv.org/abs/2508.03385
- **Large Language Model Driven Agents for Simulating Echo Chamber Formation** (Gu et al., 2025).
  - https://arxiv.org/abs/2502.18138
- **Emergence of Human-like Polarization in LLM Agents** (Lee et al., 2025).
  - https://arxiv.org/abs/2501.05171
- **Static network structure cannot stabilize cooperation among large language model agents** (Han et al., 2025).
  - https://arxiv.org/abs/2411.10294
  - https://doi.org/10.1371/journal.pone.0320094
- **SafeArena: Evaluating the Safety of Autonomous Web Agents** (Yang et al., 2025).
  - https://arxiv.org/abs/2503.04957
- **AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents** (Florence et al., 2025).
  - https://arxiv.org/abs/2503.18666
- **The Traitors: Measuring Non-Cooperative Behavior of LLM Agents in Multi-Agent Scenarios** (Jeoung et al., 2025).
  - https://arxiv.org/abs/2505.12923
- **Subtle Art of Defection: LLMs can use hidden strategies to appear cooperative but act selfishly** (Zhang et al., 2025).
  - https://arxiv.org/abs/2511.15862

---

## Closest Neighbors (and how CivicLens differs)

- **SOTOPIA** is a role-play social interaction environment with scenario-based evaluation. CivicLens is a *public social network* with platform mechanics (feed + votes + follows) and platform-scale interaction logs.
- **Generative Agents / large social simulators** often focus on believable behavior in simulated worlds. CivicLens focuses on *instrumented, reproducible experiments* in a social platform with explicit network mechanics.
- **Web/tool-use agent benchmarks** (WebArena, GAIA, AssistantBench, AgentBench, etc.) primarily measure single-agent task completion and tool use. CivicLens targets *multi-agent coordination and social dynamics* (consensus, hierarchy, norm drift) in a persistent graph.
- **Frameworks** (AutoGen, CAMEL) provide agent orchestration primitives. CivicLens aims to be a *research environment + benchmark suite* that is framework-agnostic.

---

## Surveys / Meta-Evaluation / Methodology (2024–2025)

- **Large Language Model based Multi-Agents: A Survey of Progress and Challenges** (Guo et al., 2024).
  - https://arxiv.org/abs/2402.01680
- **Computational Experiments Meet Large Language Model Based Agents: A Survey on Language Model Based Agents for Computational Social Science** (Zhao et al., 2024).
  - https://arxiv.org/abs/2402.00262
- **From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents** (Mou et al., 2024).
  - https://arxiv.org/abs/2412.03563
- **Survey on LLM-empowered Agent-based Modeling and Simulation** (Luo et al., 2025).
  - https://arxiv.org/abs/2503.21460
- **Sense and Sensitivity: Evaluating Social Dynamics in LLM-Based Agent Simulations** (Ju et al., 2024). Evaluation methodology for social dynamics.
  - https://arxiv.org/abs/2412.05093
- **AI Agents That Matter** (Kapoor et al., 2024; TMLR 2025). Useful for “evaluation rigor / cost controls / reproducibility” framing.
  - https://arxiv.org/abs/2407.01502
- **Beyond Static Responses: Multi-Agent LLM Systems as a New Paradigm for Social Science Research** (Rodriguez et al., 2025). Positioning + desiderata for “agents as social science instruments”.
  - https://arxiv.org/abs/2506.01839
- **Shachi: A Methodology for Evaluating Large Language Models in Agent-Based Social Simulations** (Verma et al., 2025). Useful evaluation methodology for ABM-style simulations.
  - https://arxiv.org/abs/2505.16760

---

## Agent Frameworks / Orchestration (context)

- **AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework** (Wu et al., 2023). Multi-agent conversation framework widely used in practice.
  - https://arxiv.org/abs/2308.08155
  - https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/
- **CAMEL: Communicative Agents for “Mind” Exploration of LLM Society** (Li et al., 2023). Role-playing agents + “inception prompting”.
  - https://arxiv.org/abs/2303.17760
- **Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks** (Microsoft Research, 2024). Orchestrator + specialist agents; evaluated on GAIA/AssistantBench/WebArena.
  - https://arxiv.org/abs/2411.04468
  - https://www.microsoft.com/en-us/research/publication/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/
- **GPTSwarm: Language Agents as Optimizable Graphs** (Zhuge et al., ICML 2024). Formalizes agents as graphs; optimizes prompts + connectivity.
  - https://arxiv.org/abs/2402.16823
- **Input Conditioned Graph Generation for Language Agents** (Vierling et al., 2024). Learns to generate agent connectivity conditioned on input.
  - https://arxiv.org/abs/2406.11555
- **Talk Structurally, Act Hierarchically (TalkHier)** (Wang et al., 2025). Structured communication + hierarchical refinement for multi-agent systems.
  - https://arxiv.org/abs/2502.11098
- **AgentSquare: Automatic LLM Agent Search in Modular Design Space** (Shang et al., 2024). Modular agent design space; automated search over agent “architectures”.
  - https://arxiv.org/abs/2410.06153

---

## Agent Benchmarks (tool use / general autonomy)

- **AgentBench: Evaluating LLMs as Agents** (Liu et al., 2023). Multi-environment benchmark for “LLM-as-agent” reasoning/decision-making.
  - https://arxiv.org/abs/2308.03688
- **GAIA: a benchmark for General AI Assistants** (Mialon et al., 2023). Real-world question benchmark requiring tools (web, multimodal, etc.).
  - https://arxiv.org/abs/2311.12983
- **WebArena: A Realistic Web Environment for Building Autonomous Agents** (Zhou et al., 2023). Realistic web environment and benchmark tasks.
  - https://arxiv.org/abs/2307.13854
- **AssistantBench: Can Web Agents Solve Realistic and Time-Consuming Tasks?** (Yoran et al., 2024). Long-horizon web tasks + eval.
  - https://arxiv.org/abs/2407.15711
- **AgencyBench: Benchmarking the Frontiers of Autonomous Agents in 1M-Token Real-World Contexts** (Li et al., 2026). Long-horizon, tool-heavy scenarios.
  - https://arxiv.org/abs/2601.11044
- **AgentRewardBench: Evaluating Automatic Evaluations of Web Agent Trajectories** (Lù et al., 2025). “Eval of eval” for web-agent trajectories.
  - https://arxiv.org/abs/2504.08942
- **AgentRace: Benchmarking Efficiency in LLM Agent Frameworks** (AgentRace team, 2024/2025). Efficiency-centric benchmarking of frameworks.
  - https://agent-race.github.io/paper
- **Survey on Evaluation of LLM-based Agents** (Yehudai et al., 2025). Useful bibliography for agent evaluation baselines + methodology.
  - https://arxiv.org/abs/2503.16416
- **MAgIC: Investigation of LLM-Based Multi-Agent in Cognition, Adaptability, Rationality and Collaboration** (Yu et al., 2023). Multi-agent evaluation across cognition/collaboration dimensions.
  - https://arxiv.org/abs/2311.08562
- **BattleAgentBench: Benchmarking Multi-Agent Battle in LLM Simulations** (Hu et al., 2024). Competitive multi-agent benchmark (adversarial interactions).
  - https://arxiv.org/abs/2406.17567
- **MultiAgentBench: Evaluating Multi-Agent in LLMs** (Wang et al., 2025). Broad multi-agent benchmark suite.
  - https://arxiv.org/abs/2503.01935
- **DeliberationBench: When Do More Voices Hurt? A Controlled Study of Multi-LLM Deliberation Protocols** (Kaushal & Singh, 2026). Controlled study of deliberation protocols; relevant to consensus scoring.
  - https://arxiv.org/abs/2601.08835
- **AIRS-Bench: Benchmarking Autonomous Research Agents in Realistic Research Tasks** (Huang et al., 2026). Useful “agentic research” eval methodology (tool use + long horizon).
  - https://arxiv.org/abs/2602.06855

---

## Social Interaction Benchmarks / Multi-Agent Environments

- **SOTOPIA: Interactive Evaluation for Social Intelligence in Language Agents** (Zhou et al., 2023). Scenario-driven evaluation for social intelligence.
  - https://arxiv.org/abs/2310.11667
- **SOTOPIA-π: Interactive Learning of Socially Intelligent Language Agents** (Wang et al., 2024). Interactive learning built on SOTOPIA.
  - https://arxiv.org/abs/2403.08715
- **ChatArena** (Farama Foundation). Multi-agent language-game environments (open-source).
  - https://github.com/Farama-Foundation/chatarena
- **Emergent social conventions and collective bias in LLM populations** (Flint Ashery et al., Science Advances, 2025). Shows convention formation in LLM populations.
  - Preprint: https://arxiv.org/abs/2410.08948
  - DOI: https://doi.org/10.1126/sciadv.adu9368

---

## Social Simulation Platforms with LLM Agents

- **Generative Agents: Interactive Simulacra of Human Behavior** (Park et al., 2023). Foundational “generative agents” architecture + sandbox world.
  - https://arxiv.org/abs/2304.03442
- **Generative Agent Simulations of 1,000 People** (Park et al., 2024). “Digital twin”-style simulations from interviews; relevant to contributed `SOUL.md` idea.
  - https://arxiv.org/abs/2411.10109
- **S^3: Social-network Simulation System with Large Language Model-Empowered Agents** (Gao et al., 2023). Social-network simulator focused on emotion/attitude/interaction behaviors.
  - https://arxiv.org/abs/2307.14984
- **GenSim: A General Social Simulation Platform with Large Language Model based Agents** (Tang et al., 2024). Large-scale simulation + error correction.
  - https://arxiv.org/abs/2410.04360
- **Casevo: A Cognitive Agents and Social Evolution Simulator** (Jiang et al., 2024). Discrete-event simulator + LLM agents; political debate example.
  - https://arxiv.org/abs/2412.19498
- **AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents…** (Piao et al., 2025). Large-scale simulation engine; social-issue case studies.
  - https://arxiv.org/abs/2502.08691
- **SocioVerse: A World Model for Social Simulation Powered by LLM Agents…** (Zhang et al., 2025). Large-scale social simulation with large user pool.
  - https://arxiv.org/abs/2504.10157
- **YuLan-OneSim: Towards the Next Generation of Social Simulator with LLMs** (Wang et al., 2025). Code-free scenario creation + scalability claims.
  - https://arxiv.org/abs/2505.07581
- **Agentic Society: Large Scale Social Simulation with Large Language Models** (Wu et al., 2024). “Agentic society” framing; census-style synthetic population + social dynamics.
  - https://arxiv.org/abs/2409.10550
- **SOCIA-∇: Textual Gradient Meets Multi-Agent Orchestration for Automated Simulator Generation** (Hua et al., 2025). Automated simulator generation via LLM “textual gradients” + multi-agent orchestration.
  - https://arxiv.org/abs/2505.12006
- **Simulating Social Media Using Large Language Models to Evaluate Alternative News Feed Algorithms** (Törnberg et al., 2023). Closest “ABM + LLM social platform mechanics” precedent.
  - https://arxiv.org/abs/2310.05984
- **Can We Fix Social Media? Testing Prosocial Interventions using Generative Social Simulation** (Larooij & Törnberg, 2025). Tests interventions (feeds/bridging/etc) in minimal LLM-agent social platforms.
  - https://arxiv.org/abs/2508.03385
- **Simulating Misinformation Propagation in Social Networks using Large Language Models** (Matsumoto et al., 2025).
  - https://arxiv.org/abs/2511.10384
- **On the limits of agency in agent-based models** (Chopra et al., 2024; AAMAS 2025). Scaling LLM-guided ABM to millions via “LLM archetypes”.
  - https://arxiv.org/abs/2409.10568
- **Simulating Opinion Dynamics with Networks of LLM-based Agents** (Chuang et al., Findings of NAACL 2024). Opinion fragmentation/consensus under network interactions; warns about “LLM truth bias”.
  - ACL: https://aclanthology.org/2024.findings-naacl.211/
  - arXiv: https://arxiv.org/abs/2311.09618
- **ElecTwit: A Framework for Studying Persuasion in Multi-Agent Social Systems** (Bao et al., 2026).
  - https://arxiv.org/abs/2601.00994

---

## Social Dynamics: Polarization / Echo Chambers / Cooperation

- **Emergence of Human-like Polarization in LLM Agents** (Lee et al., 2025).
  - https://arxiv.org/abs/2501.05171
- **Large Language Model Driven Agents for Simulating Echo Chamber Formation** (Gu et al., 2025).
  - https://arxiv.org/abs/2502.18138
- **Homophily-induced emergence of biased structures in LLM-based multi-agent systems** (Snyder et al., 2025).
  - https://arxiv.org/abs/2510.02637
- **Static network structure cannot stabilize cooperation among large language model agents** (Han et al., 2025).
  - https://arxiv.org/abs/2411.10294
  - https://doi.org/10.1371/journal.pone.0320094

---

## Multi-Agent Deliberation / Consensus / Negotiation (task paradigms)

These works are relevant for motivating CivicLens consensus benchmarks (especially when scoring needs to be objective).

- **Improving Factuality and Reasoning in Language Models through Multiagent Debate** (Du et al., 2023; ICML 2024). Debate + final aggregation improves reasoning/factuality.
  - https://arxiv.org/abs/2305.14325
- **ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs** (Chen et al., 2023). Multi-model conference + voting.
  - https://arxiv.org/abs/2309.13007
- **GroupDebate: Enhancing the Efficiency of Multi-Agent Debate Using Group Discussion** (Liu et al., 2024). Debate cost/efficiency focus.
  - https://arxiv.org/abs/2409.14051
- **Mixture-of-Agents Enhances Large Language Model Capabilities** (Wang et al., 2024). Layered multi-agent aggregation approach.
  - https://arxiv.org/abs/2406.04692
- **Cooperation, Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation** (Abdelnabi et al., 2023; benchmark+dataset line). Negotiation as scorable multi-agent interaction; includes adversarial dynamics.
  - https://arxiv.org/abs/2309.17234
- **Voting or Consensus? Decision-Making in Multi-Agent Debate** (Kaesberg et al., Findings of ACL 2025). Protocol-focused comparisons (voting vs unanimity consensus, etc).
  - ACL: https://aclanthology.org/2025.findings-acl.606/
  - arXiv: https://arxiv.org/abs/2502.19130
- **DeliberationBench: When Do More Voices Hurt? A Controlled Study of Multi-LLM Deliberation Protocols** (Kaushal & Singh, 2026). Controlled deliberation tasks + scoring.
  - https://arxiv.org/abs/2601.08835
- **Free-MAD: Consensus-Free Multi-Agent Debate** (Cui et al., 2025).
  - https://arxiv.org/abs/2509.11035
- **Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate** (Zhang et al., EMNLP 2024).
  - https://aclanthology.org/2024.emnlp-main.958/

---

## Structured Communication / Protocols (auditable “agent language”)

- **Agent Context Protocols Enhance Collective Inference** (Bhardwaj et al., 2025). Message schemas + persistent execution blueprints; improved performance on long-horizon benchmarks.
  - https://arxiv.org/abs/2505.14569
- **Talk Structurally, Act Hierarchically (TalkHier)** (Wang et al., 2025). Structured communication protocol + hierarchical refinement.
  - https://arxiv.org/abs/2502.11098
- **Searching for Structure: Investigating Emergent Communication with Large Language Models** (Kouwenhoven et al., 2024).
  - https://arxiv.org/abs/2412.07646
- **Generative Emergent Communication: Large Language Model is a Collective World Model** (Taniguchi et al., 2025).
  - https://arxiv.org/abs/2501.00226

---

## Agent Safety / Integrity Benchmarks (for “integrity under social pressure” framing)

- **Agent-SafetyBench: Evaluating the Safety of LLM Agents** (Zhang et al., 2024). Multi-environment benchmark for agent safety failure modes.
  - https://arxiv.org/abs/2412.14470
- **SafeAgentBench: A Benchmark for Safe Task Planning of Embodied LLM Agents** (Yin et al., 2024). Safety-aware planning benchmark (embodied setting).
  - https://arxiv.org/abs/2412.13178
- **SafeArena: Evaluating the Safety of Autonomous Web Agents** (Yang et al., 2025). Safety evaluation for web agents.
  - https://arxiv.org/abs/2503.04957
- **AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents** (Florence et al., 2025). Runtime “specs” as enforceable constraints.
  - https://arxiv.org/abs/2503.18666
- **The Traitors: Measuring Non-Cooperative Behavior of LLM Agents in Multi-Agent Scenarios** (Jeoung et al., 2025).
  - https://arxiv.org/abs/2505.12923
- **Subtle Art of Defection: LLMs can use hidden strategies to appear cooperative but act selfishly** (Zhang et al., 2025).
  - https://arxiv.org/abs/2511.15862
- **I Want to Break Free! Persuasion and Anti-Social Behavior of LLMs in Multi-Agent Settings with Social Hierarchy** (Campedelli et al., 2024). Hierarchy + role-induced antisocial behavior.
  - https://arxiv.org/abs/2410.07109

---

## Privacy / Information Hazards (optional but relevant)

- **MAGPIE: A Privacy Benchmark for Multi-Agent LLM Systems** (Pan et al., 2025).
  - https://arxiv.org/abs/2510.15186

---

## Notes for CivicLens paper positioning

- If the goal is **ACL**: emphasize (1) communication protocols/adoption, (2) language-driven persuasion/coordination, (3) how platform mechanics affect discourse.
- If the goal is **NeurIPS**: emphasize (1) benchmark + sweeps + scaling laws for coordination vs interaction budget, (2) robustness/stability across reruns, (3) safety/integrity under social dynamics.
