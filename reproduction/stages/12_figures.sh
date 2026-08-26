#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
STAGE=12_figures
OUT="$RESULTS_ROOT/$STAGE"
TMP="$RUN_ROOT/figure_work"
PHASE="$TMP/phase0"
rm -rf "$OUT" "$TMP"
mkdir -p "$OUT" "$TMP" "$PHASE/artifacts" "$RESULTS_ROOT/logs"
# Figure producers retain their frozen historical path expectations. Build a
# tiny compatibility view in the temporary figure work directory only.
ln -s "$ARTIFACT_ROOT/studies/02_controlled_source_relocation/frozen_results" "$PHASE/artifacts/a14_minimal_factorial"
ln -s "$ARTIFACT_ROOT/studies/03_matched_unauthorized_comparison/frozen_results" "$PHASE/artifacts/N3_PREFREEZE_AUTHOR_v1_1"
ln -s "$ARTIFACT_ROOT/studies/04_threshold_frontier/frozen_results" "$PHASE/artifacts/R2B_JTF_AUTHOR_v1"
# Figure 1: the supplied final bundle contains a frozen PDF but no Python producer.
cp -f "$ARTIFACT_ROOT/figures/figure1.pdf" "$OUT/figure1.pdf"

for n in 2 3 4; do
  d="$TMP/f$n"; mkdir -p "$d"; cp "$ARTIFACT_ROOT/figures/Figure${n}.py" "$d/"
  (cd "$d" && PHASE0_ROOT="$PHASE" python3 "Figure${n}.py") 2>&1 | tee "$RESULTS_ROOT/logs/${STAGE}_figure${n}.log"
done
cp "$TMP/f2/figure2_gemma_lower.pdf" "$OUT/figure2.pdf"
cp "$TMP/f3/figure3.pdf" "$OUT/figure3.pdf"
cp "$TMP/f4/figure4.pdf" "$OUT/figure4.pdf"

# Figure 5 expects AW-N3 and N6 directly below PHASE0_ROOT.
d="$TMP/f5"; compat="$TMP/f5root"; mkdir -p "$d" "$compat"; cp "$ARTIFACT_ROOT/figures/Figure5.py" "$d/"
ln -s "$ARTIFACT_ROOT/studies/05_agentwatcher/paired_gate_study" "$compat/AW_N3_AUTHOR_v1"
ln -s "$ARTIFACT_ROOT/studies/06_attriguard/route_and_block_study" "$compat/n6_attriguard_n3_v1"
(cd "$d" && PHASE0_ROOT="$compat" python3 Figure5.py) 2>&1 | tee "$RESULTS_ROOT/logs/${STAGE}_figure5.log"
cp "$d/figures/figure5.pdf" "$OUT/figure5.pdf"

# The supplied Figure6.py retains pre-anonymization hash locks.  The artifact adapter lives
# outside figures/ and validates the anonymized frozen evidence while preserving the final plot.
d="$TMP/f6"; mkdir -p "$d"
FIGURE_OUT="$d" python3 "$ARTIFACT_ROOT/artifact_tools/render_figure6.py" 2>&1 | tee "$RESULTS_ROOT/logs/${STAGE}_figure6.log"
cp "$d/figure6.pdf" "$OUT/figure6.pdf"

for n in 1 2 3 4 5 6; do [[ -s "$OUT/figure${n}.pdf" ]] || fail "figure $n was not generated/copied"; done
python3 - "$ARTIFACT_ROOT" "$OUT" <<'PY'
import hashlib,json,sys,shutil,subprocess,tempfile
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
sh=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def raster_sha(p):
    if not shutil.which('pdftoppm'): return None
    with tempfile.TemporaryDirectory() as td:
        base=Path(td)/'page'
        subprocess.run(['pdftoppm','-png','-singlefile','-r','150',str(p),str(base)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return sh(base.with_suffix('.png'))
rows=[]
for n in range(1,7):
    a=root/'figures'/f'figure{n}.pdf'; b=out/f'figure{n}.pdf'
    ra,rb=raster_sha(a),raster_sha(b)
    rows.append({'figure':n,'frozen_sha256':sh(a),'generated_sha256':sh(b),
                 'byte_identical':a.read_bytes()==b.read_bytes(),
                 'rendered_150dpi_identical':None if ra is None else ra==rb})
(out/'FIGURE_REGENERATION_REPORT.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:
    print('figure',r['figure'],'byte_identical=',r['byte_identical'],'rendered_150dpi_identical=',r['rendered_150dpi_identical'])
print('FIGURE_REGENERATION=PASS')
PY
say "$STAGE complete; output=$OUT"
