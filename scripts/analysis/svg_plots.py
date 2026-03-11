#!/usr/bin/env python3
"""Minimal SVG plot helpers so the analysis runs without matplotlib."""

from __future__ import annotations

import html
from pathlib import Path

COLORS = [
    "#1756a9",
    "#3d8b37",
    "#c44f00",
    "#bb1e10",
    "#7a3db8",
    "#008b8b",
    "#555555",
]


def _svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]


def _finish(path: Path, lines: list[str]) -> None:
    lines.append("</svg>")
    path.write_text("\n".join(lines))


def grouped_bar_chart(
    path: Path,
    title: str,
    x_labels: list[str],
    series: list[tuple[str, list[float]]],
    *,
    value_format: str = "{:.2f}",
    width: int = 980,
    height: int = 540,
) -> None:
    left = 80
    top = 70
    chart_width = width - 140
    chart_height = height - 170
    max_value = max((max(values) for _, values in series if values), default=1.0) or 1.0
    group_width = chart_width / max(len(x_labels), 1)
    bar_width = group_width / max(len(series) + 1, 2)

    lines = _svg_header(width, height)
    lines.append(f'<text x="{width / 2:.0f}" y="34" text-anchor="middle" font-size="22" font-family="Georgia">{html.escape(title)}</text>')

    for tick in range(6):
        value = max_value * tick / 5
        y = top + chart_height - (value / max_value) * chart_height
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="#dddddd" stroke-width="1"/>')
        lines.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="12" font-family="monospace">{value_format.format(value)}</text>')

    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#333333" stroke-width="1.5"/>')
    lines.append(f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#333333" stroke-width="1.5"/>')

    for group_idx, label in enumerate(x_labels):
        group_left = left + group_idx * group_width
        for series_idx, (name, values) in enumerate(series):
            value = values[group_idx]
            bar_height = (value / max_value) * chart_height if max_value else 0.0
            x = group_left + series_idx * bar_width + bar_width * 0.2
            y = top + chart_height - bar_height
            color = COLORS[series_idx % len(COLORS)]
            lines.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width * 0.7:.1f}" height="{bar_height:.1f}" fill="{color}" opacity="0.88"/>'
            )
            lines.append(
                f'<text x="{x + bar_width * 0.35:.1f}" y="{max(y - 6, 48):.1f}" text-anchor="middle" font-size="11" font-family="monospace">{value_format.format(value)}</text>'
            )
        lines.append(
            f'<text x="{group_left + group_width / 2:.1f}" y="{top + chart_height + 24}" text-anchor="middle" font-size="12" font-family="Georgia">{html.escape(label)}</text>'
        )

    legend_x = left
    legend_y = height - 56
    for idx, (name, _) in enumerate(series):
        color = COLORS[idx % len(COLORS)]
        x = legend_x + idx * 180
        lines.append(f'<rect x="{x}" y="{legend_y - 12}" width="14" height="14" fill="{color}"/>')
        lines.append(f'<text x="{x + 20}" y="{legend_y}" font-size="12" font-family="Georgia">{html.escape(name)}</text>')

    _finish(path, lines)


def line_chart(
    path: Path,
    title: str,
    x_labels: list[str],
    series: list[tuple[str, list[float]]],
    *,
    value_format: str = "{:.2f}",
    width: int = 980,
    height: int = 540,
) -> None:
    left = 80
    top = 70
    chart_width = width - 140
    chart_height = height - 170
    max_value = max((max(values) for _, values in series if values), default=1.0) or 1.0

    lines = _svg_header(width, height)
    lines.append(f'<text x="{width / 2:.0f}" y="34" text-anchor="middle" font-size="22" font-family="Georgia">{html.escape(title)}</text>')
    for tick in range(6):
        value = max_value * tick / 5
        y = top + chart_height - (value / max_value) * chart_height
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="#dddddd" stroke-width="1"/>')
        lines.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="12" font-family="monospace">{value_format.format(value)}</text>')
    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#333333" stroke-width="1.5"/>')
    lines.append(f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#333333" stroke-width="1.5"/>')

    x_step = chart_width / max(len(x_labels) - 1, 1)
    for idx, label in enumerate(x_labels):
        x = left + idx * x_step
        lines.append(f'<text x="{x:.1f}" y="{top + chart_height + 24}" text-anchor="middle" font-size="12" font-family="Georgia">{html.escape(label)}</text>')

    for series_idx, (name, values) in enumerate(series):
        points = []
        color = COLORS[series_idx % len(COLORS)]
        for idx, value in enumerate(values):
            x = left + idx * x_step
            y = top + chart_height - (value / max_value) * chart_height if max_value else top + chart_height
            points.append((x, y, value))
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline}"/>')
        for x, y, value in points:
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}"/>')
            lines.append(f'<text x="{x:.1f}" y="{max(y - 8, 48):.1f}" text-anchor="middle" font-size="11" font-family="monospace">{value_format.format(value)}</text>')

    legend_x = left
    legend_y = height - 56
    for idx, (name, _) in enumerate(series):
        color = COLORS[idx % len(COLORS)]
        x = legend_x + idx * 180
        lines.append(f'<line x1="{x}" y1="{legend_y - 5}" x2="{x + 18}" y2="{legend_y - 5}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<text x="{x + 24}" y="{legend_y}" font-size="12" font-family="Georgia">{html.escape(name)}</text>')

    _finish(path, lines)


def heatmap(
    path: Path,
    title: str,
    x_labels: list[str],
    y_labels: list[str],
    matrix: list[list[float]],
    *,
    value_format: str = "{:.2f}",
    width: int = 980,
    height: int = 720,
) -> None:
    left = 150
    top = 90
    chart_width = width - 220
    chart_height = height - 180
    n_cols = max(len(x_labels), 1)
    n_rows = max(len(y_labels), 1)
    cell_w = chart_width / n_cols
    cell_h = chart_height / n_rows
    flat = [value for row in matrix for value in row]
    min_value = min(flat) if flat else 0.0
    max_value = max(flat) if flat else 1.0
    span = (max_value - min_value) or 1.0

    def color_for(value: float) -> str:
        ratio = (value - min_value) / span
        red = int(255 - 110 * ratio)
        green = int(245 - 170 * ratio)
        blue = int(255 - 220 * ratio)
        return f"rgb({red},{green},{blue})"

    lines = _svg_header(width, height)
    lines.append(f'<text x="{width / 2:.0f}" y="38" text-anchor="middle" font-size="22" font-family="Georgia">{html.escape(title)}</text>')

    for row_idx, row_label in enumerate(y_labels):
        y = top + row_idx * cell_h + cell_h / 2
        lines.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-size="13" font-family="Georgia">{html.escape(row_label)}</text>')
    for col_idx, col_label in enumerate(x_labels):
        x = left + col_idx * cell_w + cell_w / 2
        lines.append(f'<text x="{x:.1f}" y="{top - 10}" text-anchor="middle" font-size="13" font-family="Georgia">{html.escape(col_label)}</text>')

    for row_idx, row in enumerate(matrix):
        for col_idx, value in enumerate(row):
            x = left + col_idx * cell_w
            y = top + row_idx * cell_h
            color = color_for(value)
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" fill="{color}" stroke="#ffffff" stroke-width="1"/>')
            lines.append(f'<text x="{x + cell_w / 2:.1f}" y="{y + cell_h / 2 + 4:.1f}" text-anchor="middle" font-size="12" font-family="monospace">{value_format.format(value)}</text>')

    _finish(path, lines)
