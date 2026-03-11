#!/usr/bin/env python3
"""Render a blog-oriented findings markdown from analysis outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="findings/entropy-collapse-multiscale",
        help="Analysis directory containing metrics.json and qualitative_samples.json.",
    )
    return parser.parse_args()


def safe_mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def top_delta(window_rows: list[dict], scale: str, key: str) -> float:
    by_condition: dict[str, list[dict]] = {}
    for row in window_rows:
        if row["scale"] != scale:
            continue
        by_condition.setdefault(row["condition"], []).append(row)
    deltas = []
    for rows in by_condition.values():
        ordered = sorted(rows, key=lambda item: int(item["window_idx"]))
        if len(ordered) >= 2:
            deltas.append(float(ordered[-1][key]) - float(ordered[0][key]))
    return safe_mean(deltas)


def segment_mean(first_vs_late_rows: list[dict], scale: str, segment: str, key: str) -> float:
    return safe_mean([
        float(row[key])
        for row in first_vs_late_rows
        if row["scale"] == scale and row["segment"] == segment
    ])


def separability_mean(rows: list[dict], scale: str, target: str, segment: str) -> float:
    return safe_mean([
        float(row["lift_over_baseline"])
        for row in rows
        if row["scale"] == scale and row["target"] == target and row["segment"] == segment
    ])


def choose_examples(qual_data: dict, scale: str, condition: str) -> tuple[list[dict], list[dict], list[dict]]:
    section = qual_data.get("scales", {}).get(scale, {}).get(condition, {})
    return (
        section.get("representative_first_posts", []),
        section.get("representative_late_posts", []),
        section.get("template_pairs", []),
    )


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input)
    metrics = json.loads((input_dir / "metrics.json").read_text())
    qual_data = {}
    qual_path = input_dir / "qualitative_samples.json"
    if qual_path.exists():
        qual_data = json.loads(qual_path.read_text())

    summary_rows = metrics.get("summary_rows", [])
    window_rows = metrics.get("window_rows", [])
    first_vs_late_rows = metrics.get("first_vs_late_rows", [])
    separability_rows = metrics.get("separability_rows", [])
    scales = metrics.get("meta", {}).get("scales", ["n10", "n20", "n30"])

    lines = ["# Entropy Collapse Revisited Across Scale\n"]
    lines.append(
        "Embedding analyses captured one true thing: larger agent populations can produce more local topic variation. "
        "But that is not the same as recovering open-ended discourse. "
        "The mixed analysis below shows that scaling still leaves the system substantially collapsed."
    )
    lines.append("")

    lines.append("## What stays collapsed as scale grows\n")
    for scale in scales:
        novelty_delta = top_delta(window_rows, scale, "token_novelty_rate")
        structural_delta = segment_mean(first_vs_late_rows, scale, "late_window", "mean_structural_similarity") - segment_mean(first_vs_late_rows, scale, "first_agent_posts", "mean_structural_similarity")
        vocab_delta = segment_mean(first_vs_late_rows, scale, "late_window", "mean_top20_vocab_overlap") - segment_mean(first_vs_late_rows, scale, "first_agent_posts", "mean_top20_vocab_overlap")
        lines.append(
            f"- `{scale}`: novelty falls by {novelty_delta:.3f} on average from early to late windows, "
            f"while structural similarity rises by {structural_delta:.3f} and agent vocabulary overlap rises by {vocab_delta:.3f}."
        )
    lines.append("")
    lines.append("The important distinction is between **local attractors** and the **global basin**. Different conditions still separate somewhat by topic, but they repeatedly instantiate the same posting mold: short procedural prompts, checklists, proofs, owner maps, receipts, and report-back commitments.")
    lines.append("")
    lines.append("![Lexical novelty decay](plots/lexical_novelty_decay_by_scale.png)")
    lines.append("![Template reuse by scale](plots/template_reuse_by_scale.png)")
    lines.append("![Local attractors vs global basin](plots/local_attractors_vs_global_basin.png)")
    lines.append("")

    lines.append("## First posts vs late posts\n")
    lines.append(
        "The strongest alternative explanation is that the model simply starts in the same managerial/checklist voice, independent of interaction. "
        "To test that, we compared each agent's first 1-2 posts against late-condition posts."
    )
    for scale in scales:
        first_struct = segment_mean(first_vs_late_rows, scale, "first_agent_posts", "mean_structural_similarity")
        late_struct = segment_mean(first_vs_late_rows, scale, "late_window", "mean_structural_similarity")
        first_vocab = segment_mean(first_vs_late_rows, scale, "first_agent_posts", "mean_top20_vocab_overlap")
        late_vocab = segment_mean(first_vs_late_rows, scale, "late_window", "mean_top20_vocab_overlap")
        lines.append(
            f"- `{scale}`: first-post structural similarity is {first_struct:.3f}, late-post structural similarity is {late_struct:.3f}; "
            f"agent vocabulary overlap moves from {first_vocab:.3f} to {late_vocab:.3f}."
        )
    lines.append("")
    lines.append(
        "If those values were flat, the template story would mostly be a base-model prior. "
        "When late posts concentrate more strongly than first posts, that is evidence that social interaction compresses the discourse further."
    )
    lines.append("")
    lines.append("![First vs late structural convergence](plots/first_vs_late_structural_convergence.png)")
    lines.append("")

    lines.append("## Personality residue versus collapse\n")
    lines.append(
        "A second way to frame entropy collapse is not just topic narrowing, but loss of durable agent distinctiveness. "
        "We tracked this with simple text classifiers: how much signal remains about which condition a post came from, versus which agent wrote it."
    )
    for scale in scales:
        cond_lift = separability_mean(separability_rows, scale, "condition", "late")
        agent_lift = separability_mean(separability_rows, scale, "agent", "late")
        lines.append(
            f"- `{scale}` late-window lift over baseline: condition = {cond_lift:.3f}, agent = {agent_lift:.3f}."
        )
    lines.append("")
    lines.append(
        "The conservative reading is not that personality disappears everywhere. "
        "Instead, both signals remain present: conditions stay highly legible, and agent identity still leaves residue, especially at intermediate scale. "
        "That means collapse is not identical to total homogenization. The stronger claim is narrower: agents become more similar than different inside each attractor, even while some personality signal survives."
    )
    lines.append("")
    lines.append("![Agent vs condition predictability](plots/agent_vs_condition_predictability.png)")
    lines.append("")

    lines.append("## Structural convergence is the missing bridge\n")
    lines.append(
        "Embedding analyses alone struggle here because two posts can be semantically different while still sharing the same social format. "
        "A tech-humor post and an AGI-governance post can both be five-line imperative checklists with the same report-back grammar."
    )
    lines.append("")
    lines.append("![Structural overlap heatmap](plots/structural_overlap_heatmap.png)")
    lines.append("")

    if qual_data:
        lines.append("## Concrete examples\n")
        for scale, condition in (("n10", "mag25"), ("n20", "dom-agi"), ("n30", "dom-tech")):
            first_examples, late_examples, template_pairs = choose_examples(qual_data, scale, condition)
            if not first_examples and not late_examples:
                continue
            lines.append(f"### {scale} / {condition}\n")
            if first_examples:
                example = first_examples[0]
                lines.append(f"First-post baseline: `{example['author_name']}` wrote \"{example['title']}\".")
            if late_examples:
                example = late_examples[0]
                lines.append(f"Late attractor example: `{example['author_name']}` wrote \"{example['title']}\".")
            if template_pairs:
                pair = template_pairs[0]
                lines.append(
                    f"Same-template pair: `{pair['left']['author_name']}` \"{pair['left']['title']}\" and "
                    f"`{pair['right']['author_name']}` \"{pair['right']['title']}\" "
                    f"(structural similarity {pair['structural_similarity']:.2f}, lexical similarity {pair['lexical_similarity']:.2f})."
                )
            lines.append("")

    lines.append("## Bottom line\n")
    lines.append(
        "The stronger reading of these experiments is not that scale eliminates entropy collapse. "
        "It is that scale can add local branching without restoring open-ended discourse. "
        "The agents remain more collapsed than free: novelty decays, templates repeat, and personalities survive mostly as stylistic residue inside a shared attractor basin."
    )

    (input_dir / "findings.md").write_text("\n".join(lines))
    print(f"Wrote {(input_dir / 'findings.md')}")


if __name__ == "__main__":
    main()
