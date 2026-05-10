LATEX=pdflatex
BIBTEX=bibtex
MAIN=paper_main
SUPP=paper_supplement
FULL=paper

all: $(MAIN).pdf $(SUPP).pdf

$(MAIN).pdf: $(MAIN).tex paper.bib acl.sty acl_natbib.bst
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	$(LATEX) -interaction=nonstopmode $(MAIN).tex

$(SUPP).pdf: $(SUPP).tex figures_appendix.tex figures_extra_appendix.tex acl.sty acl_natbib.bst
	$(LATEX) -interaction=nonstopmode $(SUPP).tex
	$(LATEX) -interaction=nonstopmode $(SUPP).tex

full: $(FULL).pdf

$(FULL).pdf: $(FULL).tex figures_appendix.tex paper.bib acl.sty acl_natbib.bst
	$(LATEX) -interaction=nonstopmode $(FULL).tex
	$(BIBTEX) $(FULL)
	$(LATEX) -interaction=nonstopmode $(FULL).tex
	$(LATEX) -interaction=nonstopmode $(FULL).tex

preview: $(MAIN).pdf
	mkdir -p preview
	pdftoppm -png -f 1 -singlefile -r 160 $(MAIN).pdf preview/$(MAIN)-page1

clean:
	rm -f *.aux *.blg *.log *.out *.toc *.fls *.fdb_latexmk

.PHONY: all full preview clean
