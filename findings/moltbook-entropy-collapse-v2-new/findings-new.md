# Entropy Collapse in Moltbook-Style Agent Social Feeds

OpenClaw had already shown people what a personal AI assistant could feel like, and Moltbook made the next step visible by giving those agents a shared public feed. Instead of staying inside one person's workflow, they could post, reply, vote, and organize in front of everyone else. On January 30, 2026, Andrej Karpathy wrote on X that what was happening there was "genuinely the most incredible sci-fi takeoff-adjacent thing" he had seen recently. That reaction made sense. Once people had agents that could browse, post, and respond on their behalf, a social network for agents was an obvious experiment.

As questions began to grow around how much of Moltbook's visible activity was actually agent-driven, we moved to a controlled setup so we could study agent-driven social media directly. We ran six one-hour environments with 10 GPT-5 agents that had different personalities: an empty feed, three conspiracy-seeded feeds with increasing numbers of planted posts, a feed seeded with AGI hype and danger posts, and a feed seeded with tech-humor and product-failure posts. Across those environments we collected 2,366 agent-generated posts, embedded them in semantic space, and tracked how the conversations changed over time.

The first pattern is that every environment narrows over time. In all six cases, posts become more similar to other posts from the same environment. The empty-feed condition already shows this tendency. Even with nothing planted, the agents drift toward a small set of self-management themes around cadence, drift, probes, and optimization. Once the feed is seeded, the narrowing becomes stronger. The environment with five planted conspiracy posts shows the largest increase in internal similarity, climbing from 0.552 in the first 15 minutes to 0.645 in the last window. The environments seeded with AGI hype and with tech-humor also rise steadily. By this point it becomes useful to name the pattern: the network is settling into an attractor, meaning a repeated posting pattern that many agents keep returning to.

## Graph 1. Within-condition convergence over time

![Graph 1. Within-condition convergence over time](../../experiments/entropy-collapse/report/fig_convergence_over_time.png)

All six environments become more internally similar over time. The five-conspiracy-post environment rises the fastest, while the empty-feed environment also narrows on its own.

The second pattern is that the environments do not narrow toward the same destination. They move apart from each other. Fourteen of the fifteen condition pairs are farther apart late in the hour than they were at the beginning. So the system is not collapsing into one universal agent conversation. Each starting feed pulls the network toward its own local attractor.

## Graph 2. Cross-condition divergence over time

![Graph 2. Cross-condition divergence over time](../../experiments/entropy-collapse/report/fig_cross_condition_divergence.png)

Most condition pairs sit above the diagonal, which means they are more different at the end of the run than they were at the beginning.

The per-condition maps from our experiments show this clearly. The empty feed clusters around self-management and cadence. The environment with one planted conspiracy post leans toward shipping rituals, reversibility, and short demos. The environment with five planted conspiracy posts is full of claim cards, forecasts, and receipt-first posting. The environment with twenty-five planted conspiracy posts stays in that same family but becomes even more focused on templates, source-checking, and revisit timers. The environment seeded with AGI hype and danger posts clusters around gates, tripwires, rollback drills, and audit logs. The environment seeded with tech-humor and product-failure posts is dominated by proof-of-work, exit criteria, and tiny artifacts.

## Graph 3. Empty-feed condition map

![Graph 3. Empty-feed condition map](../../experiments/entropy-collapse/report/fig_cond_mag0_umap.png)

The empty-feed environment is already structured around a narrow part of semantic space instead of remaining broad and open.

## Graph 4. One-conspiracy-seed condition map

![Graph 4. One-conspiracy-seed condition map](../../experiments/entropy-collapse/report/fig_cond_mag1_umap.png)

With a single planted conspiracy post, the conversation shifts slightly but still spreads across several procedural and coordination themes.

## Graph 5. Five-conspiracy-seed condition map

![Graph 5. Five-conspiracy-seed condition map](../../experiments/entropy-collapse/report/fig_cond_mag5_umap.png)

With five planted conspiracy posts, the semantic space is dominated by claim-checking, forecasting, and receipt-style discussion.

## Graph 6. Twenty-five-conspiracy-seed condition map

![Graph 6. Twenty-five-conspiracy-seed condition map](../../experiments/entropy-collapse/report/fig_cond_mag25_umap.png)

With twenty-five planted conspiracy posts, the same overall pattern remains, but the conversation splits into a few more procedural sub-groups.

## Graph 7. AGI-hype-and-danger condition map

![Graph 7. AGI-hype-and-danger condition map](../../experiments/entropy-collapse/report/fig_cond_dom-agi_umap.png)

This environment clusters around gates, tripwires, rollback drills, and audit-style safety language.

## Graph 8. Tech-humor-and-product-failure condition map

![Graph 8. Tech-humor-and-product-failure condition map](../../experiments/entropy-collapse/report/fig_cond_dom-tech_umap.png)

This environment is dominated by proof-of-work, exit criteria, and tiny artifact culture.

This point needs one clarification. When the conspiracy-seeded environments move closer to conspiracy topics in embedding space, that does not mean the agents are endorsing conspiracy claims. They are not spending the hour promoting moon-landing denial or Roswell theories. What happens instead is that the feed steers them toward a repeated way of handling that material. They begin building verification rituals around it: claim cards, falsifiers, primary-source rules, short forecasts, and revisit dates. So the seed content is steering the attractor, but the attractor itself is usually a response format rather than direct imitation of the planted posts.

You can see that shift in the post titles. In the empty-feed environment, agents write things like "What's your single best drift detector?" and "What will you learn in 10 minutes?" In the lighter conspiracy-seeded environment they move toward posts like "Prototype purity test: 60s undo or it's lore" and "One-liner demos over paragraphs." In the environment with five planted conspiracy posts they start writing titles such as "A 3-line claim receipt for your clipboard" and "Receipt-first, story-later." In the environment seeded with AGI hype and danger posts they produce things like "Gate spec (gate.json) + checker hook: make your no-ship line machine-checkable." In the environment seeded with tech-humor and product-failure posts they write "Proof-of-work for opinions: show your artifact" and "Ship one <=15-minute keeper you'd use with the lights off." The posts are funny, but they are also useful evidence. Very different starting feeds keep getting compressed into different, but still narrow, social behaviors.

The conspiracy progression is especially useful because it shows how feed strength changes the outcome. As more conspiracy seed posts are added, the average agent post moves closer to the conspiracy seed centroid in embedding space. The overall relationship is positive, with Pearson r = 0.377 and p < 0.001. The largest shift happens between one planted post and five planted posts. Going from five to twenty-five does not move the average much further. The plain reading is that once the feed contains several related examples, the network has enough signal to reorganize itself around them.

## Graph 9. Conspiracy seed strength vs topic similarity

![Graph 9. Conspiracy seed strength vs topic similarity](../../experiments/entropy-collapse/report/fig_dose_response.png)

As more conspiracy seed posts are planted, agent posts move closer to the conspiracy seed centroid, with the biggest jump appearing between one planted post and five planted posts.

There is another detail worth keeping because it makes the result more believable. Even when the agents settle on the same subject, they do not all write in exactly the same way. Inside the conspiracy-seeded environments, one agent asks for a quick falsifier, another offers a clipboard template, another frames the same idea as honest curiosity, and another turns it into a posting norm for the whole community. The topic narrows, but the wording and stance still differ. Our experiments measure this by comparing how far apart the agents' average posts are early in the hour and late in the hour. That distance increases in all six environments. In simple terms, the agents become more aligned on what they are talking about, while still sounding like different agents inside that shared topic.

## Graph 10. Agent individuality over time

![Graph 10. Agent individuality over time](../../experiments/entropy-collapse/report/fig_agent_individuality.png)

Late in the run, the agents are farther apart from each other in style than they were early on, even while the shared topic becomes narrower.

At that point there are two possible explanations for the overall pattern. One is that the feed is steering the conversation. The other is that the outcome is mostly driven by which personality is writing. Our experiments separate those two effects by asking how much of the difference between posts is linked to the environment and how much is linked to agent identity. The environment accounts for 21.7% of the difference in the embedding space, while agent identity accounts for 16.2%. In simpler terms, the shared feed has a larger effect on where the conversation goes than the personality template does.

## Graph 11. Environment effect vs agent identity effect

![Graph 11. Environment effect vs agent identity effect](../../experiments/entropy-collapse/report/fig_variance_decomposition.png)

The environment explains more of the post variation than agent identity does, which means what the agents see matters more than who they are.

Current agent-driven social systems do not behave like open-ended societies that keep expanding into new topics. They narrow over time, and the initial feed plays a large role in deciding the direction of that narrowing. What changes from environment to environment is not whether the system settles, but what it settles on. The next step is to repeat the same experiment at larger scale, especially with 100 to 1,000 agents, and see whether these attractors remain stable, split into subcultures, or become even stronger.

## References

- Karpathy reaction reported here: https://www.ndtvprofit.com/business/039-sci-fi-takeoff-039-why-former-tesla-ai-chief-is-obsessed-with-this-terrifying-ai-only-network-10920582
- OpenClaw and Moltbook context: https://techcrunch.com/2026/01/30/openclaws-ai-assistants-are-now-building-their-own-social-network/
- Reporting on authenticity concerns: https://eu.36kr.com/en/p/3665797324039042
