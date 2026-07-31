# Paper source snapshot

`source/` is the complete ZIP export downloaded from the author-designated Overleaf project. It is preserved without pruning so the main paper, supplementary packet, figures, bibliography, style files, and the export's own archive remain traceable.

- Primary entry point: `source/main.tex`
- Supplement entry point: `source/supplement.tex`
- Export SHA-256: recorded in `../sources.lock.json`
- Recommended build: `latexmk -pdf main.tex`

The manuscript source is not covered by the repository's MIT code license. No scientific claims were silently rewritten during artifact cleanup.

`source/archive/main.pdf` is retained as provenance from the Overleaf export. Its embedded title and build timestamp show that it is an earlier compile, so it must not be treated as a fresh build of the current `main.tex`. The offline verifier checks every referenced TeX input, bibliography, and figure. A fresh PDF build still requires a local TeX distribution or Overleaf.
