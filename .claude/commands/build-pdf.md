Compile DESCRIPTION.tex to PDF using the full LaTeX + BibTeX cycle.

Run the following commands in sequence inside `/home/plateny/mestrado/mestrado`:

```bash
cd /home/plateny/mestrado/mestrado && pdflatex -interaction=nonstopmode DESCRIPTION.tex && bibtex DESCRIPTION && pdflatex -interaction=nonstopmode DESCRIPTION.tex && pdflatex -interaction=nonstopmode DESCRIPTION.tex
```

Report whether the compilation succeeded or show any errors from the output.
