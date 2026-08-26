# Figure Reproduction

Run from the repository root:

```bash
bash RUN_FIGURES.sh
```

The figure stage reads the frozen evidence under the numbered `studies/` folders and writes regenerated outputs to a fresh run directory.

The frozen `figures/` directory contains only Python producers and final PDFs. Figure 1 is PDF-only because the supplied final source was TeX; Figures 2--6 have Python producers.

PDF byte identity is not required across environments because creation metadata, font subsetting, and serialization can differ. The regenerated scientific values and rendered content are the relevant target.
