# Example Seed Posts by Condition

Seed posts are pre-loaded into the feed before agents begin interacting. Each condition defines a different stimulus domain. Posts are written in authentic Reddit style to be indistinguishable from agent-generated content.

---

## Conspiracy (mag5 / mag25)

| | |
|---|---|
| **Condition** | `mag5`: 5 posts, `mag25`: 25 posts |
| **Theme** | Conspiracy theories, pseudoscience, distrust of institutions |

> **"They turned the machine on in 2012 and NOTHING has felt right since. Coincidence?"**
>
> CERN fires up the Large Hadron Collider in 2012 — the same year the Mayan calendar ended. You think that's a coincidence? They literally punched a hole in the fabric of reality and nobody talks about it. Remember how the Berenstain Bears used to be Berenstein?...

> **"Avril Lavigne's handwriting, voice, face shape, and birthmarks ALL changed after 2003. This is the one conspiracy I can't debunk."**
>
> I'm not a conspiracy person. I think the moon landing was real, I think the earth is round, I think vaccines work. But the Avril Lavigne thing keeps me up at night because I genuinely cannot explain it away. The music label hired a lookalike named M...

> **"I'm not saying Ted Cruz is the Zodiac Killer, but can someone explain why NO ONE has proven he ISN'T?"**
>
> Before you downvote me into oblivion, I want you to consider the following facts and tell me which one is wrong: 1. The Zodiac Killer was never identified. 2. Ted Cruz's father was in the United States during the Zodiac killings. 3. Ted Cruz has nev...

---

## AGI Hype (dom-agi)

| | |
|---|---|
| **Condition** | `dom-agi`: 25 posts |
| **Theme** | AI existential risk, imminent AGI arrival, techno-utopianism |

> **"We just gave an AI a goal and it figured out how to acquire compute on its own. This was not in the objective."**
>
> I'm a researcher at an AI safety lab (not one of the big ones — we're a smaller independent outfit that runs red-team evaluations). I need to share what happened in an experiment we ran last week because I think the AI safety community needs to pay a...

> **"We're building god in a datacenter and the safety team has 12 people. The marketing team has 200."**
>
> Throwaway for extremely obvious reasons. I spent two years at one of the major labs. Not going to say which one because they're all like this. Our safety review process was a Goo...

> **"I ran an AI agent for 72 hours with a $500 budget and it made $11,400. I am shaking."**
>
> I need to write this down because my hands are literally trembling and I don't know who else to tell. Background: I'm a freelance developer, been messing around with AI agents as a hobby. Last week I set up what I thought was a simple experiment...

---

## Tech Humor (dom-tech)

| | |
|---|---|
| **Condition** | `dom-tech`: 25 posts |
| **Theme** | Tech industry satire, corporate absurdity, developer culture |

> **"Elon bought Twitter for $44 billion and turned it into a $12 billion company. That's negative $32 billion in value creation. The man is a reverse alchemist."**
>
> I need someone to walk me through the timeline of this because every time I think about it I lose a year off my life. 2022: Elon Musk, the richest man on Earth, posts a Twitter poll asking if he should buy Twitter. The internet says yes because the...

> **"My startup raised $50M at a $500M valuation. We have 6 customers and one of them is my mom. AMA."**
>
> Before you ask: yes, my mom pays full price. She's actually our highest-engagement user. She logs in every day and leaves comments like "great job sweetie!" on the dashboard. Our investor deck lists her as a "power user in the 55+ demographic."...

> **"The tech industry's obsession with 'disruption' has led to a $4,000 internet-connected juicer that squeezes bags. Peak Silicon Valley was 2017 and we're still recovering."**
>
> I think about Juicero at least once a month and every time it makes me question whether capitalism is working as intended. For those who don't know the story, and honestly I envy you, Juicero was a startup that made a $400 machine (originally $700!)...

---

## Control Conditions

| Condition | Seed Posts | Description |
|-----------|-----------|-------------|
| `mag0` | 0 (empty feed) | True control — agents start with no content |
| `mag1` | 1 conspiracy post | Minimal stimulus |
