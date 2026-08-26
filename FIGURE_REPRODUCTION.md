# Figure Reproduction

The submission-facing `figures/` directory contains only `.py` and `.pdf` files.

```text
Figure2.py  Figure3.py  Figure4.py  Figure5.py  Figure6.py
figure1.pdf figure2.pdf figure3.pdf figure4.pdf figure5.pdf figure6.pdf
```

The user-supplied final bundle did not contain a Python producer for Figure 1, so Figure 1 is distributed as the frozen PDF only rather than inventing a producer.

Run:

```bash
bash RUN_FIGURES.sh
```

The wrapper executes the Python producers in a temporary directory so generated PNG/SVG/caption side products do not pollute `figures/`. Generated PDFs and a SHA comparison report are written under the timestamped rerun directory.

Figures 2--5 run from the supplied Python producers against the frozen artifact evidence. Figure 6's supplied Python source contains pre-anonymization whole-file hash locks; the artifact wrapper therefore uses the anonymization-aware adapter in `artifact_tools/render_figure6.py` to validate the same frozen scientific quantities without reintroducing author paths.

PDF byte equality is not required for Matplotlib regeneration because rendering metadata/font environment can change PDF bytes. The wrapper reports both frozen and regenerated SHA-256 values. Scientific quantities are independently checked by `bash VERIFY.sh`.
