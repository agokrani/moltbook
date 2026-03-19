# Theme And Masters

## Canvas

- Slide size is `9144000 x 5143500` EMU.
- That equals `10 x 5.625 in`, which is standard `16:9`.
- Both active slide masters use a solid `lt1` background, so the default canvas is plain white.

## Active theme wiring

| Master | Bound theme | Effective role |
| --- | --- | --- |
| `slideMaster1.xml` | `theme2.xml` | Primary system; used on 130 slides |
| `slideMaster2.xml` | `theme3.xml` | Alternate accent system; used on 23 slides |

Observations:

- `theme2.xml` is a blue-led "Simple Light" palette: `4285F4`, `212121`, `78909C`, `FFAB40`, `0097A7`, `EEFF41`.
- `theme3.xml` keeps the same neutral base but makes orange more prominent by setting `accent1=FFAB40`.
- `theme1.xml` exists in the package but does not appear to be attached to either active slide master.

## Master behavior

Both masters are intentionally sparse. Each contains only three persistent placeholders:

1. Title
2. Body
3. Slide number

The slide number placeholder uses the literal token `‹#›`, which behaves like a small footer/page marker across the deck.

Implication:

- The deck does not rely on decorative master artwork.
- Most of the visible look comes from per-slide content placement, imported images, and lightweight annotation shapes.

## Layout families actually used

Only a few layout families drive most of the deck:

| Layout family | Slides |
| --- | ---: |
| `Title only` | 57 |
| `Title and body` | 27 |
| `Title only 1 1` | 23 |
| `Title and two columns` | 22 |
| `Title slide` | 10 |
| `Blank` | 8 |
| `Main point` | 3 |
| `Title slide 1` | 2 |
| `Title and Content` | 1 |

Notes:

- `Title only 1 1` behaves like a title-plus-subtitle variant.
- The deck technically ships with 30 layouts, but the actual presentation collapses into 6 to 8 practical templates.
- `slideMaster2.xml` appears mainly on opener, transition, and appendix-style clusters rather than throughout the whole deck.

## Repeated geometry cues

Common title box patterns:

- Standard left title: `x=0.26`, `y=0.24`, `w=9.32`, `h=0.63 in`
- Tight top title variant: `x=0.23`, `y=0.15`, `w=9.32`, `h=0.63 in`
- Centered opener title: `x=0.26`, `y=0.74`, `w=9.66`, `h=1.95 in`

Interpretation:

- The deck keeps titles close to the top edge.
- Left-title slides preserve a narrow top margin and a broad central content area.
- Section or cover slides switch to a centered, taller title frame.

## Reusable template rules

- Keep the base template white and structurally minimal.
- Build around these core layouts: cover, title-only, title-plus-body, title-plus-subtitle, two-column, blank.
- Keep slide numbers enabled.
- Treat the master as a skeleton, not as the source of decorative style.
- Use the blue-led master as the default and the orange-led master for cover, bridge, or appendix moments.

