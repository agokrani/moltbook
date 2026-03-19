# Reference Deck Format Notes

Source deck: `slides/20251010_MultiAgent_latest_ZhijingJin.pptx`

This folder captures reusable format rules from the reference deck so future presentations can stay visually and structurally consistent with it.

## Scope

- Analysis method: PPTX package and XML inspection, plus parallel subagent passes over theme/layout, visual language, and content conventions.
- Rendering limitation: these notes are based on document structure and style metadata, not a full slide-by-slide visual render.
- Practical takeaway: the deck's real house style comes more from repeated content patterns and local overrides than from a heavy PowerPoint master theme.

## Core constants

- Canvas: 16:9 widescreen, `10 x 5.625 in`
- Slides: 153
- Slide masters: 2
- Layouts: 30 total, but only a small set is used repeatedly
- Theme parts: 3 total, with `theme2.xml` and `theme3.xml` bound to the active masters
- Media: 240 assets, mostly PNGs
- Image-bearing slides: 117
- Native chart objects: 0
- Speaker notes with real content: 56
- Comment files: 20

## What matters most

- White canvas, minimal master chrome, and small footer-style slide numbers
- Descriptive, role-based titles such as `Motivation`, `Results`, `Simulation`, and `Takeaway`
- Lato-driven typography in practice, even though the bound themes still declare Arial
- Image-first slides with thin-outline annotation shapes rather than decorative backgrounds
- Notes used for elaboration; slides stay visually light

## Files

- `01_theme_and_masters.md`: canvas, theme wiring, master behavior, layout families
- `02_typography_and_visual_language.md`: fonts, sizes, color system, shapes, spacing cues
- `03_slide_patterns_and_narrative.md`: recurring slide types, title conventions, notes/comments usage
- `04_recreation_checklist.md`: compact rules for building new decks in the same format

