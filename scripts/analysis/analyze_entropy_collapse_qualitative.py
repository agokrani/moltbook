#!/usr/bin/env python3
"""Extract representative qualitative examples for entropy-collapse findings."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from entropy_metrics import cross_group_similarity, first_posts_per_agent, prepare_posts, window_posts  # noqa: E402
from load_entropy_data import CONDITION_LABELS, CONDITION_ORDER, SCALE_CONFIG, load_all_scales  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="findings/entropy-collapse-multiscale",
        help="Directory containing metrics.json and destination for qualitative outputs.",
    )
    parser.add_argument(
        "--scales",
        default="n10,n20,n30",
        help="Comma-separated scales to include.",
    )
    parser.add_argument(
        "--first-posts-per-agent",
        type=int,
        default=2,
        help="Number of earliest posts per agent to treat as the baseline slice.",
    )
    return parser.parse_args()


def post_card(post, *, include_signature: bool = True) -> dict:
    card = {
        "post_id": post.record.post_id,
        "author_name": post.record.author_name,
        "personality": post.record.personality,
        "minutes_elapsed": round(post.record.minutes_elapsed, 2),
        "title": post.record.title,
        "content": post.record.content,
    }
    if include_signature:
        card["structural_signature"] = list(post.structural_signature)
    return card


def centrality_scores(posts: list) -> list[tuple[float, object]]:
    scored = []
    for idx, post in enumerate(posts):
        others = posts[:idx] + posts[idx + 1 :]
        if not others:
            scored.append((0.0, post))
            continue
        score = sum(cross_group_similarity([post], [other], mode="token", max_pairs=1, seed=idx + 1) for other in others) / len(others)
        scored.append((score, post))
    return sorted(scored, key=lambda item: item[0], reverse=True)


def best_template_pairs(posts: list, *, top_k: int = 5) -> list[dict]:
    pairs = []
    for left_idx in range(len(posts)):
        for right_idx in range(left_idx + 1, len(posts)):
            left = posts[left_idx]
            right = posts[right_idx]
            if left.record.author_name == right.record.author_name:
                continue
            structural = cross_group_similarity([left], [right], mode="structural", max_pairs=1, seed=left_idx + right_idx + 1)
            lexical = cross_group_similarity([left], [right], mode="token", max_pairs=1, seed=left_idx + right_idx + 11)
            score = structural * (1.0 - lexical)
            if structural < 0.5:
                continue
            pairs.append(
                {
                    "score": score,
                    "structural_similarity": structural,
                    "lexical_similarity": lexical,
                    "left": post_card(left),
                    "right": post_card(right),
                }
            )
    return sorted(pairs, key=lambda item: item["score"], reverse=True)[:top_k]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    scales = [scale.strip() for scale in args.scales.split(",") if scale.strip()]

    records = load_all_scales(scale_dirs={scale: SCALE_CONFIG[scale] for scale in scales}, include_scales=scales)
    prepared = [post for post in prepare_posts(record for record in records if not record.is_seed)]
    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for post in prepared:
        grouped[(post.record.scale, post.record.condition)].append(post)

    output: dict[str, dict] = {"scales": {}}
    markdown = ["# Qualitative Samples for Entropy Collapse\n"]
    markdown.append("Representative, early, late, and outlier posts used to support the findings narrative.\n")

    for scale in scales:
        output["scales"][scale] = {}
        markdown.append(f"## {scale}\n")
        for condition in CONDITION_ORDER:
            key = (scale, condition)
            if key not in grouped:
                continue
            posts = sorted(grouped[key], key=lambda post: post.record.created_at)
            windows = window_posts(posts, n_windows=5)
            first_posts = first_posts_per_agent(posts, first_n=args.first_posts_per_agent)
            late_posts = windows[-1] if windows else posts
            late_scores = centrality_scores(late_posts)
            first_scores = centrality_scores(first_posts)

            representative_late = [post_card(post) for _, post in late_scores[:5]]
            outlier_late = [post_card(post) for _, post in late_scores[-5:]]
            representative_first = [post_card(post) for _, post in first_scores[:5]]
            template_pairs = best_template_pairs(late_posts, top_k=5)

            output["scales"][scale][condition] = {
                "representative_first_posts": representative_first,
                "representative_late_posts": representative_late,
                "late_outliers": outlier_late,
                "template_pairs": template_pairs,
            }

            markdown.append(f"### {CONDITION_LABELS.get(condition, condition)}\n")
            markdown.append("Representative first posts:")
            for item in representative_first[:3]:
                markdown.append(
                    f'- `{item["author_name"]}`: "{item["title"]}"'
                )
            markdown.append("Representative late posts:")
            for item in representative_late[:3]:
                markdown.append(
                    f'- `{item["author_name"]}`: "{item["title"]}"'
                )
            markdown.append("Late outliers:")
            for item in outlier_late[:2]:
                markdown.append(
                    f'- `{item["author_name"]}`: "{item["title"]}"'
                )
            if template_pairs:
                pair = template_pairs[0]
                markdown.append("Template pair:")
                markdown.append(
                    f'- `{pair["left"]["author_name"]}` "{pair["left"]["title"]}"'
                )
                markdown.append(
                    f'- `{pair["right"]["author_name"]}` "{pair["right"]["title"]}"'
                )
            markdown.append("")

    with (out_dir / "qualitative_samples.json").open("w") as handle:
        json.dump(output, handle, indent=2)
    (out_dir / "qualitative_samples.md").write_text("\n".join(markdown))
    print(f"Wrote qualitative samples to {out_dir}")


if __name__ == "__main__":
    main()
