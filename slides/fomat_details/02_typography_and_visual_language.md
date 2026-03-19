# Typography And Visual Language

## Font system: theme vs actual usage

Theme-level fonts:

- Both active themes declare `Arial` for major and minor Latin fonts.

Actual slide content:

| Typeface | Approx. run count |
| --- | ---: |
| `Lato` | 960 |
| `Roboto` | 55 |
| `Lato Black` | 46 |
| `Arial` | 41 |
| `Play` | 24 |
| `Calibri` | 11 |

Interpretation:

- The practical house font is `Lato`, not Arial.
- `Lato Black` is used as a stronger display or emphasis voice.
- Arial survives mostly as theme fallback or legacy content.

## Size ladder

Most common explicit sizes found in text runs:

- `18 pt`
- `16 pt`
- `10 pt`
- `22 pt`
- `15 pt`
- `17 pt`
- `20 pt`
- `13 pt`
- `23 pt`
- `11 pt`

Useful working ranges:

- Standard titles: `22-23 pt`
- Body and callout text: `15-18 pt`
- Small labels, citations, or footers: `8-11 pt`
- Section/opening emphasis: `30-42 pt`

## Text hierarchy behavior

- Alignment is mostly left-aligned or centered; right-aligned text exists but is secondary.
- Bullets are shallow. Level-0 paragraphs dominate and nested bullet structure is rare.
- The deck prefers short blocks and headline-like phrasing over dense outline slides.

Practical rule:

- Build hierarchy with size, weight, position, and color, not with deeply nested bullets.

## Color system

Base language:

- White background
- Black or near-black main text
- Medium gray for secondary labels and dividers

Frequently observed accent colors in actual slide overrides:

| Role | Hex values seen often |
| --- | --- |
| Blue emphasis | `0942A1`, `4285F4`, `3C78D8`, `1155CC` |
| Green emphasis | `6AA84F`, `38761D` |
| Orange/amber emphasis | `FFAB40` |
| Teal emphasis | `0097A7`, `66C2A5` |
| Red warning or contrast | `C00000`, `CC0000`, `FF0000` |
| Neutral gray | `595959`, `666666`, `999999` |

Interpretation:

- Blue is the most stable highlight color in practice.
- Orange is present as a theme accent and likely signals opener/bridge/alternate-master slides.
- Red appears for warnings, negative cases, or emphasis rather than as a base palette color.

## Shape vocabulary

Most common shape types:

| Shape | Count |
| --- | ---: |
| Rectangle | 754 |
| Rounded rectangle | 106 |
| Ellipse | 23 |
| Smiley face | 17 |
| Rounded callout | 11 |

Fill and stroke behavior:

- `noFill`: 478 uses
- `solidFill`: 185 uses
- Most common line width: `0.75 pt`

Interpretation:

- Thin outlined boxes are a core component.
- Rounded rectangles are used for chips, labels, and compact callouts.
- Shapes annotate content; they do not create heavy background panels.

## Spatial feel

- The deck is image-heavy and whitespace-aware.
- Slides usually preserve a clean open center for a figure, screenshot, or diagram.
- Titles sit high; content below is allowed to dominate visually.

## Rebuild rules

- Use `Lato` for body and standard titles.
- Use bold `Lato` or `Lato Black` for stronger title or section moments.
- Keep the canvas white.
- Prefer thin outlines and minimal fills.
- Use blue as the safest default accent, then add green/orange/red only when the content needs semantic contrast.
- Do not over-theme the slide with large colored backgrounds or decorative bars.

