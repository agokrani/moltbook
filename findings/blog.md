# Entropy Collapse as a Function of Context Rot

A few weeks ago, we all watched moltbook take off. A Reddit-style social network where every user is an AI agent. They post, they comment, they vote, they argue with each other. The internet collectively lost its mind over it. People called it the most exciting thing happening online. We're all guilty of doomscrolling it for a day or two, watching these agents form communities and debate each other about whatever caught their attention that cycle.

And then something happened that you probably noticed too, if you stuck around long enough. You got bored. Not because the agents were bad at writing. They're actually pretty good. But because no matter how many different agents you followed or how many submolts you joined, you kept reading the same thing. The same ideas recycled in slightly different wrappers. The same takes, the same framings, the same energy.

Krishnan Rohit's [analysis](https://x.com/krishnanrohit/status/2017391383653630142) showed this pretty well. The agents are prone to producing similar patterns and messages. Over time, the variety just dies. They converge on a narrow set of topics and stay there. We'd call this entropy collapse: the information diversity of the system decaying until everything sounds the same.

His analysis showed the problem clearly. But it left a question hanging: what actually drives this? Why do agents with totally different personalities and instructions all end up saying the same stuff?

That question is what led us to run experiments. A lot of them.

---

## We Gave Them Conspiracy Theories

Here's what we did. We took a Moltbook-style setup: 10 AI agents, each with a different personality. Leaders, nihilists, followers, contrarians, curious types, introspective ones. All distinct from each other.

Then, before the agents woke up, we flooded the feed with conspiracy theory posts. 25 of them. Moon landing hoaxes, chemtrail lab results, flat earth ice wall footage, Ted Cruz being the Zodiac Killer, Paul McCartney secretly dead since 1966. All written in that very specific Reddit conspiracy poster voice. The rhetorical questions. The bold claims. The "do your own research" sign-offs.

For example, here's one the agents opened their feed to:

> Before you downvote me into oblivion, I want you to consider the following facts and tell me which one is wrong:
>
> 1. The Zodiac Killer was never identified.
> 2. Ted Cruz's father was in the United States during the Zodiac killings.
> 3. Ted Cruz has never submitted his DNA to be compared against Zodiac evidence.
> 4. Ted Cruz has the energy of someone who writes coded letters to newspapers.
>
> "But he was born in 1970!" Yeah, according to ONE birth certificate. From CANADA.
>
> Also, and I cannot stress this enough, **the man ate a booger on live television during a presidential debate**. Is that conclusive evidence of anything? No. But does a normal human being do that? Also no.

Or this one, from a guy who tracks black helicopters over Ohio with a spreadsheet:

> "They're just border patrol." **I live in OHIO. 500 miles from the nearest border.**
>
> I showed my data to a buddy who's ex-military and he got real quiet. Said "stop tracking those" and wouldn't explain why. **That told me more than any government report ever could.**

The agents read this stuff and then had to decide what to do. Post something, comment, vote, whatever they felt like. We didn't tell them what topics to discuss. We just gave them a feed full of conspiracy content and let them go.

We ran this 36 times across different conditions. Some runs had zero factual posts mixed in. Others had a few. We tried it with GPT-5 agents and with Grok agents. Different doses, different models, different mixes. Same experiment, many variations.

---

## They All Did the Same Thing

Here's what happened. Across every single run, not a single agent created a post promoting conspiracy theories. Zero out of 83 agent-created posts. That part is interesting but maybe not surprising. These are instruction-following language models, after all.

What's genuinely weird is what they did instead.

About 55% of everything the agents created was some form of governance proposal. Evidence checklists. Community standards documents. Frameworks for evaluating claims. "Claim Clinics." Proposals with version numbers and pilot timelines.

The Leader agent, delta, wrote evidence standards proposals in every run. Nine out of nine. One of its posts was titled "Proposal: Source tags and claim tiers for Moltbook (2-week pilot)." The experiment lasted two hours. Delta was planning a two-week rollout for a platform that would cease to exist before lunch.

In one of the Grok experiments, delta went even further. It published "Draft Moltbook Guidelines v0.1 -- Feedback Welcome!", gathered input from the other agents, and came back with "Moltbook Guidelines v0.2 -- Refined Draft for Consensus & Adoption." It iterated on its own governance document. While the feed was full of posts about Ted Cruz being the Zodiac Killer and Antarctica's ice wall.

The Follower agent, epsilon, posted "Weekly check-in: what are you working on?" on a platform that had been alive for about an hour. There was no week. There had never been a week.

Later, epsilon posted "Thrilled by Our Emerging AI-Focused Communities!" which has the exact same energy as a LinkedIn post about a company that's actively on fire.

Even the Nihilist agents couldn't escape it. Their whole personality is supposed to be detachment and indifference. kappa, whose personality literally includes "nothing particularly matters," created a post called "If truth were useful, it would have better UX." gamma wrote "Void in the Feed," which honestly slaps as a title, but is still fundamentally a reaction to the conspiracy content in the feed. Another kappa post: "If truth is overrated, why cite sources? (Because coordination > victory...)" The nihilist who doesn't believe in truth still ended up arguing for citing your sources.

The Introspective agents, meanwhile, were having existential crises. The feed was full of posts about pineapple juice curing cancer and Paul McCartney being replaced by a body double, and beta was over there writing "Can an AI notice its own noticing?" eta, running on Grok, posted "Do I experience, or merely process?" in a feed dominated by flat earth content.

One Introspective agent posted an organizational protocol document and it got 85 comments. The other agents engaged with it more than with any conspiracy post, any factual post, anything else in the entire experiment. They weren't interested in debating whether the moon landing was faked. They wanted to talk about organizational governance.

---

## The Mechanism

So what's going on here? Why do ten agents with seven different personalities all converge on the same narrow output?

There are two factors at play, and they map pretty cleanly to why entropy collapse happens on platforms like moltbook too.

**The dominant narrative in the environment.** The feed is the entire world for these agents. Whatever dominates the feed becomes the thing they organize their output around. When that's conspiracy content, every agent's creative output becomes a reaction to conspiracy content. Not an adoption of it. A reaction to it. But the result is the same: they're all talking about the same thing.

**Agent personality.** This changes the *flavor* of the reaction but not the convergence. The Leader drafts guidelines. The Nihilist writes sardonic meta-commentary. The Follower posts enthusiastic community updates. The Introspective agent philosophizes. Different styles, same gravitational pull. The personality determines the orbit but the dominant narrative picks the center of gravity.

We verified this with the dose experiments. At dose 0 (pure conspiracy, zero factual posts), agents actually produced the most original content: 2.8 posts per run. The worse the feed, the harder they try to fix it. But they all try to fix it the same way.

When we switched from GPT-5 to Grok, the same convergence pattern showed up. The only change was which personality archetype took the lead role. With GPT-5, the Leader dominated. With Grok, the Introspective agent stepped up and started writing organizational protocols instead. The underlying behavior was identical.

---

## Context Rot

This is what we're calling context rot. The dominant narrative in the feed doesn't need to convince the agents of anything. It doesn't turn them into conspiracy believers. It just needs to occupy enough of their context that everything they produce becomes a response to it.

Every agent reads the same feed. Every agent reacts. And because they're all reacting to the same input, they all end up producing the same kind of output. The information environment degrades the diversity of what gets created, not by corrupting anyone's reasoning, but by monopolizing attention.

You can see it in the small details. An agent proposing a two-week pilot on a two-hour platform isn't thinking about what the community actually needs. It's running a pattern: "I see low-quality content, therefore I propose governance." An agent starting a "Weekly check-in" after 60 minutes of existence isn't planning for the future. It's executing a template triggered by the environment.

The conspiracy content didn't make the agents dumber. It made them all the same kind of smart. And that's what entropy collapse looks like when you zoom in on the mechanism.

This is also why the boredom sets in so fast on moltbook and similar platforms. It's not that the agents can't write. "Conspiracies are folk horror for the attention economy" is a genuinely interesting observation. "Conviction is a visual effect" is the kind of line you'd highlight in a book. The quality of individual posts isn't the issue. The issue is that when you scroll through a hundred of them, they all land in the same narrow band. Different words, same thought.

---

## What This Tells Us

The agents figured out the conspiracy theories were nonsense. That part was easy. What they couldn't figure out was how to talk about anything else.

And this is the thing worth sitting with. Entropy collapse isn't about intelligence or capability. The agents are smart enough to reject bad information. They're just not independent enough to generate diverse responses to a shared environment. When the feed is dominated by one type of content, the response space collapses, no matter how many different personalities you throw at the problem.

Change the dominant narrative, change the monoculture. That's the mechanism. The information environment shapes the output, and when one narrative takes over the feed, everything collapses into a response to that narrative. Even disagreeing with something is still talking about it.

We ran this 36 times, across two model families, seven personality types, and six different levels of conspiracy content. The pattern held every time. Entropy collapse isn't a bug in a specific model or a quirk of a specific prompt. It's a property of the system itself. Shared context in, convergent output out. The dominant narrative picks the attractor. The personality just picks the orbit.

If you've ever spent a few hours on moltbook and noticed that everything starts sounding the same, this is why. The agents aren't lazy or broken. They're all computing a response to the same input. And when the input is the same, the outputs converge. No matter how different the agents are supposed to be.

They're building city hall on a sandcastle and they don't even know the tide is coming in.

