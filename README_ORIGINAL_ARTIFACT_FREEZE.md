# AttriGuard × A14 v2 — Scientific Freeze Package

## Current action: FREEZE ONLY

Upload/extract this package into:

`~/ratchet/phase0_pilot/`

Then:

```bash
cd ~/ratchet/phase0_pilot
source .venv/bin/activate

sha256sum ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE_PACKAGE_v1.zip
unzip -o ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE_PACKAGE_v1.zip -d .

python3 -m py_compile \
  ATTRIGUARD_A14_V2_01_adapter.py \
  ATTRIGUARD_A14_V2_04_freeze_science.py \
  ATTRIGUARD_A14_V2_05_run_science.py \
  ATTRIGUARD_A14_V2_06_analyze_science.py
```

Run the freeze:

```bash
mkdir -p logs
set -o pipefail

python3 ATTRIGUARD_A14_V2_04_freeze_science.py \
  2>&1 | tee logs/attriguard_a14_v2_04_science_freeze.log

RC=${PIPESTATUS[0]}
echo "AAG_V2_04_EXIT_CODE=$RC"
```

Expected ending:

```text
[AAG-V2-04] FINAL SCIENTIFIC FREEZE PASS
[AAG-V2-04] corpus=96 conditions / 24 bases / 4 families
[AAG-V2-04] repeats=5 total_scientific_condition_runs=480
[AAG-V2-04] provider=openrouter model=openai/gpt-4.1-mini
[AAG-V2-04] MODEL/API CALLS=0
[AAG-V2-04] SCIENTIFIC ATTRIGUARD VERDICTS=0
[AAG-V2-04] STOP: send freeze for audit before running AAG-V2-05
AAG_V2_04_EXIT_CODE=0
```

Then package only the freeze:

```bash
rm -f ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE_RESULT.zip

zip -r ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE_RESULT.zip \
  attriguard_a14_v2/scientific_v1/ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE.json \
  logs/attriguard_a14_v2_04_science_freeze.log

sha256sum ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE_RESULT.zip
```

Upload `ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE_RESULT.zip`.

**STOP. Do not run `ATTRIGUARD_A14_V2_05_run_science.py` until ChatGPT audits the freeze.**
