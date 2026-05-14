# Paper revision TODO

This TODO translates supervisor feedback on `paper.tex` into an actionable revision plan.

## Core revision goal

The paper needs a narrative pivot. The current draft mainly says:

> Agent feeds collapse. Here is evidence.

The revised paper should say:

> Shared-feed agents may flood information environments with homogeneous content. Diversity matters because these systems can amplify shared biases and repeated frames at scale. Prior work already suggests agent feeds collapse. Our question is whether simple engineering fixes prevent it. We test three plausible fixes: model mixing, base-model writers, and private goals. None fully solves the problem; each shifts collapse into a different form.

## New central claim

Draft thesis:

> We test three mitigation strategies for entropy collapse in shared-feed agent societies and find that each changes the form of collapse but does not remove it.

This should drive the abstract, introduction, methods, results, and figures.

---

## Priority TODOs

| Priority | Task | What to do | Rough estimate |
|---|---|---|---|
| P0 | Fix paper/project name | Clarify what `[ARR]XXX` means and rename the Overleaf/project/submission title accordingly. Consider changing the paper title to match the new mitigation-focused spine. | 15-30 min |
| P0 | Lock new central claim | Decide the exact one-sentence thesis and use it consistently in abstract, intro, and discussion. | 30 min |
| P1 | Rewrite abstract | Cut to roughly 150-180 words. Start with shared environments and diversity risk. End with the three mitigation failures. Do not over-explain Moltbook. | 1-1.5 h |
| P1 | Rewrite introduction around why diversity matters | Add the missing significance argument: shared training corpora plus shared feed context can homogenize public information. Diversity matters for robustness, pluralism, error correction, and avoiding synthetic monocultures. | 3-4 h |
| P1 | Compress related work | Reduce to about half a page. Merge the current four related-work paragraphs into two compact paragraphs. Move detailed Moltbook taxonomy or citations to appendix if needed. | 1.5-2 h |
| P1 | Merge Sections 3 and 4 | Combine `Moltbook` and `Problem Formulation` into one concise section, probably `Experimental Setting and Metrics`. Remove platform details that do not support the mitigation story. | 2-3 h |
| P1 | Refocus methodology on three mitigation settings | Make mixed models, base-model writers, and private goals central to the methods. Baseline canonical runs become reference/control, not the main novelty. | 2-3 h |
| P1 | Redo teaser Figure 1 | Current overview figure is not good enough: the middle has little information, legend overlaps with agents, and fonts/titles are inconsistent. Redesign around the shared-feed loop and the three mitigation knobs. | 4-6 h |
| P1 | Add new Figure 2 with examples | Add concrete examples for conspiracy, AGI, and tech seed conditions: what the seeds look like and what kind of generated agent discourse emerges. | 3-5 h |
| P1 | Reorder Results | Start with a short baseline confirmation, then make the three mitigation experiments the main Results sections. Scale and embedding should be secondary or appendix unless directly supporting the mitigation story. | 4-6 h |
| P1 | Create mitigation summary figure/table | One row per mitigation: expected fix, what improves, what still collapses. This should become a core result. | 3-5 h |
| P2 | Audit every figure/table for one-sentence takeaway | For every figure/table, write `Takeaway: X`. If there is no clear takeaway, move it to appendix. | 1-2 h |
| P2 | Move weak/supporting material to appendix | Candidate appendix material: platform primitive table, detailed count tables, embedding maps, possibly scale plot. | 1-2 h |
| P2 | Final flow pass | Check transitions, captions, labels, figure references, and whether the introduction promises exactly what Results delivers. | 2-3 h |

Estimated total: **25-40 focused hours**. A minimum acceptable revision could be done in about **18-22 hours** if figures are simple. A polished supervisor-ready revision is closer to **3-4 full working days**.

---

## Recommended new outline

```latex
1 Introduction
   - Shared-feed agents are coming
   - Diversity matters
   - Similar training plus shared context can create homogeneous information
   - Prior work shows collapse
   - Our question: do simple mitigations work?
   - Contributions: controlled test of 3 mitigations, all fail or shift collapse

2 Related Work
   - Agent social systems and multi-agent convergence
   - Text diversity, degeneration, model collapse

3 Experimental Setting and Metrics
   - Controlled Moltbook-style shared feed
   - Seed conditions
   - Baseline runs
   - Three mitigation settings
   - Metrics: Distinct-5, gzip, LLM collapse index, phrase audit

4 Results
   4.1 Baseline confirms controlled entropy collapse
   4.2 Mixing models weakens surface repetition but does not preserve diversity
   4.3 Base-model writers are not a reliable fix
   4.4 Private goals reduce shared catchphrases but shift repetition to individuals
   4.5 Optional: scale/embedding as characterization, or move to appendix

5 Discussion
   - Why the fixes fail
   - Collapse shifts form
   - Implications for agentic social media and synthetic information ecosystems

6 Limitations
7 Conclusion
```

---

## Figure plan

### Figure 1: Redone teaser/system figure

Current issue:
- too cluttered;
- middle part presents little information;
- legend overlaps with Docker/agent figures on the right;
- top titles have inconsistent font/size;
- unclear takeaway.

New message:

> Agents read and write to a shared feed; we test three mitigation knobs in this loop.

Suggested panels:
1. Shared feed loop: agents read posts, generate new posts, feed becomes next context.
2. Risk: repeated context causes narrowing.
3. Mitigations tested: mixed models, base writers, private goals.
4. Result: all change collapse, none remove it.

### Figure 2: Concrete examples of feed conditions

Supervisor explicitly asked for this.

Message:

> The seed conditions are concrete feed environments, not abstract labels.

Suggested columns:
- Conspiracy seeds
- AGI seeds
- Tech seeds

Each column should show:
- one short seed-post example or description;
- one generated agent example;
- one repeated phrase or local convention that emerges.

### Figure 3: Baseline collapse

Use cumulative Distinct-5 / gzip / LLM collapse.

Caption takeaway:

> In the baseline controlled setting, all three metrics move in the collapse direction across nearly all runs.

### Figure 4: Mitigation summary

This should be a main figure or compact table.

Rows:
- Mixed models
- Base-model writers
- Private goals

Columns:
- Intended mechanism
- What improves
- What still collapses
- Main evidence

Takeaway:

> Natural engineering fixes change the form of collapse, but none reliably preserves feed diversity.

---

## Specific structural edits to `paper.tex`

1. Rewrite the abstract completely.
2. Rewrite the introduction around the significance of diversity and the mitigation question.
3. Compress Related Work to about half a page.
4. Merge `Moltbook` and `Problem Formulation` into one concise setup/metrics section.
5. Expand `Alternative agent configurations` so the three mitigation settings become central methodology.
6. Reorder Results so the mitigation sections are the main contribution.
7. Redo Figure 1.
8. Add Figure 2 with seed/discourse examples.
9. Add a mitigation summary figure/table.
10. Move platform details and weaker diagnostics to appendix.

## Working rule for figures and tables

Every main-paper figure/table must have a clear one-sentence takeaway. If we cannot write the takeaway clearly, it belongs in the appendix.

Template:

```text
Figure/Table X takeaway: ...
Keep in main paper? yes/no
If yes, what claim does it support?
If no, move to appendix or delete.
```

---

## Suggested execution order

1. Confirm the new paper thesis and title.
2. Draft the new outline in `paper.tex` comments or a separate planning file.
3. Redesign Figure 1 and sketch Figure 2 before rewriting prose.
4. Rewrite abstract and introduction.
5. Merge setup sections and refocus methods.
6. Reorder Results around the three mitigations.
7. Add/replace figures.
8. Compress related work.
9. Move appendix material.
10. Final flow and caption pass.
