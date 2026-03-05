# Ranking Effect Experiment — Related Literature

> **Scope**: Focused on Reddit-based experimental studies of vote manipulation, position bias, and ranking effects. Non-Reddit papers listed separately as supporting context.

---

## Reddit-Based Studies

### 1. Random Voting Effects in Social-Digital Spaces (Glenski, Johnston & Weninger, 2015)
- **Citation**: Glenski, M., Johnston, T. J., & Weninger, T. (2015). Random Voting Effects in Social-Digital Spaces: A case study of Reddit Post Submissions. *Proc. 26th ACM Conference on Hypertext & Social Media (HT '15)*, pp. 293-297.
- **arXiv**: https://arxiv.org/abs/1506.01977
- **Local PDF**: `papers/glenski2015-random-voting-effects.pdf`
- **Platform**: Reddit (first in-vivo Reddit experiment, IRB approved by Notre Dame + Air Force)
- **Design**: Sept 1, 2013 – Jan 31, 2014 (6 months). Computer program scanned Reddit every 2 minutes. Most recent post randomly assigned to +1, -1, or control with equal probability. Random delay 0–60 min. Re-sampled 4 days later. **N = 93,019 posts** (30,998 up, 30,796 down, ~31,225 control). Treatments removed from scores before analysis.
- **Key findings**:
  - +1 nudge → **+11.02%** final rating on average
  - +1 nudge → **+24.6%** increased probability of reaching front page (score ≥2000)
  - -1 nudge → **-5.15%** final rating on average
  - **Both up and down effects significant** (contradicts Muchnik's no-downvote finding)
  - Treatment delay had little effect on mean outcome
  - Effects are subreddit-dependent (significant in AdviceAnimals, AskReddit, videos)
  - Scores extremely right-skewed (skewness=11.2, kurtosis=149.8)
  - Only ~0.25% of Reddit visitors actually vote
- **Relevance**: **Most comparable to our Moltbook experiment.** Same ±1 nudge on posts with score-based ranking. First to show downvotes matter on Reddit.

### 2. Rating Effects on Social News Posts and Comments (Glenski & Weninger, 2017)
- **Citation**: Glenski, M. & Weninger, T. (2017). Rating Effects on Social News Posts and Comments. *ACM Transactions on Intelligent Systems and Technology (TIST)*, 8(6).
- **arXiv**: https://arxiv.org/abs/1606.06140
- **DOI**: 10.1145/2963104
- **Local PDF**: `papers/glenski2017-rating-effects.pdf`
- **Platform**: Reddit
- **Design**: Two large-scale in-vivo experiments extending the 2015 study:
  - **Experiment 1 (Posts)**: N = 93,019 (same data as 2015)
  - **Experiment 2 (Comments)**: N = 128,316 comments, same ±1 random treatment
  - Same methodology: scan every 2 min, random ±1 with random delay, re-sample later
- **Key findings**:
  - Posts: +1 → **+11.02%**; -1 → **-5.15%** (confirms 2015)
  - Comments: +1 → **NO positive herding**; -1 → **-37.4%** rating decrease
  - Probability of high rating: **+24.6%** for up-treated posts; **-46.6%** for down-treated comments
  - **"Contrary to Muchnik"**: confirmed negative herding on Reddit
  - Posts and comments have different herding dynamics
  - Subreddit-dependent: 22% of top 500 subs had significant up effects, 21.6% had significant down effects
- **Relevance**: Largest ±1 nudge study on a live platform. Key insight: posts and comments respond differently. Our experiment targets posts.

### 3. Consumers and Curators: Browsing and Voting Patterns on Reddit (Glenski, Pennycuff & Weninger, 2017)
- **Citation**: Glenski, M., Pennycuff, C., & Weninger, T. (2017). Consumers and Curators: Browsing and Voting Patterns on Reddit. *IEEE Transactions on Computational Social Systems*.
- **arXiv**: https://arxiv.org/abs/1703.05267
- **Local PDF**: `papers/glenski2017-consumers-curators.pdf`
- **Platform**: Reddit (browser extension tracking 309 users for 1 year, Aug 2015 – Jul 2016)
- **Design**: Complete activity logs (~2 million interactions) capturing all clicks, pageloads, and votes. Observational, not experimental.
- **Key findings**:
  - **73% of posts were voted on without the user reading the content**
  - **4x position bias**: users ~4x more likely to interact with post at rank 1 vs rank 10
  - Sharp drop in interaction at rank 25 (Reddit's pagination boundary)
  - Cognitive fatigue: voting accuracy decreases during longer browsing sessions
  - Posts more likely to be browsed/voted from within subreddit than from front page
- **Relevance**: Establishes the position bias mechanism on Reddit that our nudge exploits. A ±1 vote shifts post rank → shifted position gets 4x differential attention → cascading effect.

### 4. Manipulating Visibility of Political and Apolitical Threads on Reddit via Score Boosting (Carman et al., 2018)
- **Citation**: Carman, M., Koerber, M., Li, J., Choo, K.-K. R., & Ashman, H. (2018). Manipulating visibility of political and apolitical threads on Reddit via score boosting. *IEEE TrustCom/BigDataSE 2018*, pp. 184-191.
- **DOI**: 10.1109/TrustCom/BigDataSE.2018.00037
- **Local PDF**: `papers/score-boosting-reddit-2018.pdf`
- **Platform**: Reddit (AskReddit + The_Donald subreddits)
- **Design**: Compared sets of threads whose visibility was artificially boosted via vote manipulation against control threads.
- **Contains Reddit's hot algorithm source code**:
  ```python
  score = upvotes - downvotes
  scorepoints = log10(max(abs(score), 1))
  # + time component
  ```
- **Key findings**:
  - Vote manipulation has significant impact on thread visibility and user engagement
  - Effects observed in both political (The_Donald) and apolitical (AskReddit) subreddits
  - Only top 25 posts visible per page; post at rank 150 is essentially invisible
  - Only ~10% of users view page 2 of results
- **Relevance**: Demonstrates practical vote manipulation on Reddit. Contains the actual hot algorithm we replicate in Moltbook. Shows the visibility cliff — posts outside top 25 are effectively invisible.

### 5. Popularity and Quality in Social News Aggregators (Stoddard, 2015)
- **Citation**: Stoddard, G. (2015). Popularity and Quality in Social News Aggregators: A Study of Reddit and Hacker News. *WWW '15 Companion*, pp. 815-818.
- **arXiv**: https://arxiv.org/abs/1501.07860
- **Local PDF**: `papers/stoddard2015-popularity-quality-reddit.pdf`
- **Platform**: Reddit + Hacker News
- **Design**: Observational study using Poisson regression to estimate "intrinsic quality" of posts, controlling for position bias.
- **Key findings**:
  - Popularity on Reddit is a stronger reflection of intrinsic quality than expected
  - Small early differences in votes lead to highly inconsistent final outcomes
  - Position bias and rich-get-richer dynamics confirmed
- **Relevance**: Provides the theoretical framework for why ±1 nudges can cascade — early vote differences compound through ranking feedback loops.

---

## Non-Reddit Supporting Context

### 6. Social Influence Bias (Muchnik, Aral & Taylor, 2013, Science)
- **Citation**: Muchnik, L., Aral, S., & Taylor, S. J. (2013). Social influence bias: A randomized experiment. *Science*, 341(6146), 647-651.
- **DOI**: 10.1126/science.1240466
- **Local PDF**: `papers/muchnik2013-social-influence-bias.pdf`
- **Platform**: **Undisclosed** social news aggregation site (NOT Reddit — legally cannot disclose; comments NOT ranked by score)
- **Design**: 101,281 comments, ±1 vote at creation, 5 months
- **Key findings**: +32% next positive vote, +25% final score. Downvotes corrected (NO negative herding).
- **Note**: The no-downvote-effect finding was later contradicted by Glenski on actual Reddit. Difference likely due to platform — Muchnik's site did not rank content by score.

### 7. The Ranking Effect (2025)
- **Citation**: The Ranking Effect: How Algorithmic Rank Influences Attention on Social Media. arXiv:2509.18440
- **Local HTML**: `papers/ranking-effect-2025.html`
- **Platform**: Simulated Reddit r/popular (screenshots, NOT live Reddit)
- **Design**: 10×2 factorial, 585 humans, controlled rank position
- **Key findings**: ~40% less engagement at lower ranks. Social proof (vote counts) had NO effect.
- **Note**: Name inspiration for our experiment. Shows position matters more than displayed scores.

### 8. Leveraging Position Bias (Lerman & Hogg, 2014, PLoS ONE)
- **Citation**: Lerman, K. & Hogg, T. (2014). Leveraging Position Bias to Improve Peer Recommendation. *PLoS ONE*, 9(6): e98914.
- **DOI**: 10.1371/journal.pone.0098914
- **Local PDF**: `papers/lerman2014-position-bias.pdf`
- **Platform**: Amazon Mechanical Turk (NOT Reddit — tested with science stories)
- **Design**: 5 visibility policies (random, popularity, activity, fixed, reverse) on MTurk
- **Key findings**: **5x** more attention to items at top of list vs bottom. Ordering by activity (recency) produces better quality estimates than ordering by popularity.
- **Note**: Quantifies position bias magnitude, relevant mechanism for our experiment.

---

## Comparison Table (Reddit Studies Only)

| Dimension | Glenski 2015 | Glenski 2017 (TIST) | Glenski 2017 (IEEE) | Carman 2018 | **Our Experiment** |
|-----------|-------------|---------------------|---------------------|-------------|-------------------|
| Type | ±1 nudge RCT | ±1 nudge RCT | Observational | Observational | ±1 nudge RCT |
| Target | Posts | Posts + Comments | Browsing+Voting | Thread visibility | Posts |
| N | 93,019 posts | 93k posts + 128k comments | 309 users, 2M events | 2 subreddits | ~125 world posts/mode |
| Upvote effect | +11.02% | +11.02% posts, none comments | N/A | Significant visibility boost | ~equal to control (prelim) |
| Downvote effect | -5.15% | -5.15% posts, -37.4% comments | N/A | N/A | Score halved (prelim) |
| Position bias | Implied | Implied | **4x (rank 1 vs 10)** | Top 25 visible | Via hot algorithm |
| Duration | 6 months | 6 months | 1 year | N/A | 1 hour per run |
| Participants | Reddit users | Reddit users | Reddit users | Reddit users | **AI agents (10)** |

## Key Takeaways for Our Experiment

1. **Our design mirrors Glenski 2015/2017**: same ±1 nudge on posts with score-based ranking on a Reddit-like platform
2. **Expected human baselines**: +11% for upvotes, -5.15% for downvotes (Glenski posts)
3. **Position bias mechanism**: 4x attention differential (Glenski 2017 IEEE) + visibility cliff at rank 25 (Carman 2018)
4. **Our preliminary AI agent results** show stronger downward and weaker upward effects — consistent with Glenski's direction but different magnitudes
5. **Novel contribution**: first ±1 nudge experiment with AI agents as participants instead of humans
6. **Hot algorithm**: Moltbook uses same `log10(score) + time` formula as Reddit (documented in Carman 2018)
