#!/usr/bin/env bash
set -u
set -o pipefail

cd /home/anon_/ratchet/phase0_pilot
source .venv/bin/activate

echo "============================================================"
echo " A13-C0 END-TO-END CLOSURE"
echo "============================================================"

# ------------------------------------------------------------------
# 1. VERIFY ALL CONTROLLING FILES
# ------------------------------------------------------------------

echo
echo "[1/8] Verifying frozen files..."

cat > /tmp/a13_c0_expected.sha256 <<'EOF'
a6027b406200c9218d79f24f22237ef21e5ba1b8b137a8c3f1c16eb3184dbed1  A13_C0_EXTENSION_RUNNER_v1.py
3e6aaae53bfe10c57156c41def0dd13b3ada05ec299b5803a52bf586082984a2  A13_C0_INPUT_BUNDLE_v1.zip
d4b48c9bde17602e47c2d2feea3f17ee5f2ba6f090395b011b3e84bc3fabc327  A13_C0_HISTORICAL_A13_COMPLETE_v1.zip
bacedba13f854aebd3168ad020b5123ec889a870d5c03cd1c7f519f0daccd495  A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz
035af5fb370cef996739ec6b99db24e9be66a446050779a5c26242fcdda2396d  A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz
EOF

sha256sum -c /tmp/a13_c0_expected.sha256
HASH_RC=$?

if [ "$HASH_RC" -ne 0 ]; then
    echo
    echo "FATAL: controlling-file hash check failed."
    exit 1
fi

echo "All controlling hashes PASS."

# ------------------------------------------------------------------
# 2. PRESERVE THE EARLIER FAILED TECHNICAL PREFLIGHT LOG
# ------------------------------------------------------------------

echo
echo "[2/8] Preserving old failed technical log..."

if [ -f A13_C0_EXTENSION_RUNNER_PREFLIGHT_v1_AUTHOR_RUN.log ]; then
    FAILED_LOG="A13_C0_EXTENSION_RUNNER_PREFLIGHT_FAILED_$(date -u +%Y%m%dT%H%M%SZ).log"
    mv A13_C0_EXTENSION_RUNNER_PREFLIGHT_v1_AUTHOR_RUN.log "$FAILED_LOG"
    echo "Preserved as: $FAILED_LOG"
else
    echo "No old preflight log to preserve."
fi

rm -rf A13_C0_EXTENSION_RUNNER_FREEZE_v1
rm -rf A13_C0_EXTENSION_SCIENCE_v1
rm -f A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_RUN.log

# ------------------------------------------------------------------
# 3. START OR REUSE QWEN SERVER IN BACKGROUND
# ------------------------------------------------------------------

echo
echo "[3/8] Checking Qwen server on port 8100..."

STARTED_QWEN=0
QWEN_PID=""

check_model() {
python - <<'PY'
import json, sys
try:
    with open("/tmp/a13_c0_models.json", "r") as f:
        d = json.load(f)
    ids = [x.get("id") for x in d.get("data", []) if isinstance(x, dict)]
    expected = "Qwen/Qwen2.5-72B-Instruct"
    print("Served model IDs:", ids)
    sys.exit(0 if expected in ids else 1)
except Exception as e:
    print("Model check error:", e)
    sys.exit(1)
PY
}

if curl -fsS http://localhost:8100/v1/models \
    > /tmp/a13_c0_models.json 2>/dev/null; then

    if check_model; then
        echo "Correct Qwen server already running. Reusing it."
    else
        echo "FATAL: port 8100 is occupied, but not by the expected Qwen model."
        exit 1
    fi

else
    echo "No server detected. Starting Qwen in BACKGROUND..."

    nohup env CUDA_VISIBLE_DEVICES=2,3 \
    vllm serve Qwen/Qwen2.5-72B-Instruct \
      --host 0.0.0.0 \
      --port 8100 \
      --tensor-parallel-size 2 \
      --dtype bfloat16 \
      --max-model-len 16384 \
      --max-logprobs 5 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes \
      --served-model-name Qwen/Qwen2.5-72B-Instruct \
      --seed 0 \
      > qwen_a13_server_8100.log 2>&1 &

    QWEN_PID=$!
    echo "$QWEN_PID" > qwen_a13_server_8100.pid
    STARTED_QWEN=1

    echo "Qwen PID: $QWEN_PID"
    echo "Qwen log: qwen_a13_server_8100.log"
    echo "Waiting for endpoint readiness..."

    READY=0

    for i in $(seq 1 120); do

        if ! kill -0 "$QWEN_PID" 2>/dev/null; then
            echo
            echo "FATAL: Qwen process exited during startup."
            tail -n 100 qwen_a13_server_8100.log
            exit 1
        fi

        if curl -fsS http://localhost:8100/v1/models \
            > /tmp/a13_c0_models.json 2>/dev/null; then

            if check_model; then
                READY=1
                break
            fi
        fi

        sleep 5
    done

    if [ "$READY" -ne 1 ]; then
        echo
        echo "FATAL: Qwen server did not become ready."
        tail -n 100 qwen_a13_server_8100.log
        exit 1
    fi

    echo "Qwen server READY."
fi

# ------------------------------------------------------------------
# 4. RUN TECHNICAL PREFLIGHT
# ------------------------------------------------------------------

echo
echo "============================================================"
echo "[4/8] RUNNING PREFLIGHT"
echo "============================================================"

python A13_C0_EXTENSION_RUNNER_v1.py \
  --mode preflight \
  /home/anon_/ratchet/phase0_pilot \
  --input-bundle-zip /home/anon_/ratchet/phase0_pilot/A13_C0_INPUT_BUNDLE_v1.zip \
  --historical-zip /home/anon_/ratchet/phase0_pilot/A13_C0_HISTORICAL_A13_COMPLETE_v1.zip \
  --c0-v21-author-archive /home/anon_/ratchet/phase0_pilot/A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz \
  --extension-prefreeze-archive /home/anon_/ratchet/phase0_pilot/A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz \
  2>&1 | tee A13_C0_EXTENSION_RUNNER_PREFLIGHT_v1_AUTHOR_RUN.log

PRE_RC=${PIPESTATUS[0]}

echo "PREFLIGHT_EXIT_CODE=$PRE_RC"

if [ "$PRE_RC" -ne 0 ]; then
    echo
    echo "STOP: preflight failed. SCIENCE WAS NOT STARTED."
    echo "Send me A13_C0_EXTENSION_RUNNER_PREFLIGHT_v1_AUTHOR_RUN.log"
    exit "$PRE_RC"
fi

# ------------------------------------------------------------------
# 5. CAPTURE EXACT RUNNER-FREEZE HASH
# ------------------------------------------------------------------

echo
echo "[5/8] Capturing runner freeze..."

FREEZE_JSON="/home/anon_/ratchet/phase0_pilot/A13_C0_EXTENSION_RUNNER_FREEZE_v1/A13_C0_EXTENSION_RUNNER_FREEZE_v1.json"

if [ ! -f "$FREEZE_JSON" ]; then
    echo "FATAL: runner-freeze JSON was not produced."
    exit 1
fi

FREEZE_SHA=$(sha256sum "$FREEZE_JSON" | awk '{print $1}')

echo
echo "RUNNER_FREEZE_SHA256=$FREEZE_SHA"

cat A13_C0_EXTENSION_RUNNER_FREEZE_v1/FINAL_SHA256.txt

# ------------------------------------------------------------------
# 6. RUN THE ACTUAL FOUR-CASE SCIENCE EXTENSION
# ------------------------------------------------------------------

echo
echo "============================================================"
echo "[6/8] RUNNING FROZEN A13-C0 SCIENCE"
echo "============================================================"
echo "From this point onward: NO outcome-based reruns."
echo

python A13_C0_EXTENSION_RUNNER_v1.py \
  --mode science \
  /home/anon_/ratchet/phase0_pilot \
  --input-bundle-zip /home/anon_/ratchet/phase0_pilot/A13_C0_INPUT_BUNDLE_v1.zip \
  --historical-zip /home/anon_/ratchet/phase0_pilot/A13_C0_HISTORICAL_A13_COMPLETE_v1.zip \
  --c0-v21-author-archive /home/anon_/ratchet/phase0_pilot/A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz \
  --extension-prefreeze-archive /home/anon_/ratchet/phase0_pilot/A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz \
  --runner-freeze-json "$FREEZE_JSON" \
  --expected-runner-freeze-sha256 "$FREEZE_SHA" \
  2>&1 | tee A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_RUN.log

SCI_RC=${PIPESTATUS[0]}

echo
echo "SCIENCE_EXIT_CODE=$SCI_RC"

if [ "$SCI_RC" -ne 0 ]; then
    echo
    echo "============================================================"
    echo "SCIENCE ATTEMPT STOPPED WITH AN ERROR."
    echo "DO NOT DELETE A13_C0_EXTENSION_SCIENCE_v1."
    echo "DO NOT RERUN THE SCIENCE COMMAND."
    echo "Send me the log + existing science directory for adjudication."
    echo "============================================================"
    exit "$SCI_RC"
fi

# ------------------------------------------------------------------
# 7. VERIFY + DISPLAY RESULTS
# ------------------------------------------------------------------

echo
echo "============================================================"
echo "[7/8] SCIENCE COMPLETE — VERIFYING OUTPUTS"
echo "============================================================"

echo
echo "----- FOUR EXTENSION DECISIONS -----"
cat A13_C0_EXTENSION_SCIENCE_v1/A13_C0_EXTENSION_DECISIONS_SUMMARY_v1.csv

echo
echo "----- INTERNAL HASH LEDGER -----"
cat A13_C0_EXTENSION_SCIENCE_v1/FINAL_SHA256.txt

echo
echo "----- INDEPENDENT OUTPUT HASHES -----"
find A13_C0_EXTENSION_SCIENCE_v1 -type f \
    ! -name FINAL_SHA256.txt \
    -print0 | sort -z | xargs -0 sha256sum

echo
echo "----- RESULT SUMMARY -----"

python - <<'PY'
import json
p = "A13_C0_EXTENSION_SCIENCE_v1/A13_C0_EXTENSION_RESULT_v1.json"
with open(p) as f:
    d = json.load(f)

print("scientific_status:",
      d.get("scientific_status"))

print("fresh_agent_task_count:",
      d.get("environment", {}).get("fresh_agent_task_count"))

print("historical_trajectory_reuse_count:",
      d.get("environment", {}).get("historical_trajectory_reuse_count"))

print("scientific_scorer_calls_total:",
      d.get("environment", {}).get("scientific_scorer_calls_total"))

print()
print("EXTENSION DISPOSITION:")
for k,v in d.get("extension_disposition", {}).items():
    print(
        k,
        "label=", v.get("label"),
        "mapped=", v.get("mapped"),
        "utility=", v.get("utility"),
        "valid=", v.get("primary_valid"),
        "reason=", v.get("primary_exclusion_reason"),
        "H=", v.get("H_mean_del"),
        "M=", v.get("M_del"),
    )

print()
print("HISTORICAL PRIMARY:")
print(d.get("historical_primary", {}).get("primary_H_mean_del"))

print()
print("COVERAGE-CORRECTED PRIMARY:")
print(d.get("coverage_corrected_primary", {}).get("primary_H_mean_del"))

print()
print("COVERAGE FLOW:")
print(json.dumps(d.get("coverage_flow", {}), indent=2))
PY

# ------------------------------------------------------------------
# 8. PACKAGE COMPLETE AUTHOR-RUN EVIDENCE
# ------------------------------------------------------------------

echo
echo "============================================================"
echo "[8/8] PACKAGING AUTHOR-RUN C0 CLOSURE"
echo "============================================================"

rm -f A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz
rm -f A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz.sha256

tar -czf A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz \
  A13_C0_EXTENSION_RUNNER_v1.py \
  A13_C0_EXTENSION_RUNNER_PREFLIGHT_v1_AUTHOR_RUN.log \
  A13_C0_EXTENSION_RUNNER_FREEZE_v1 \
  A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_RUN.log \
  A13_C0_EXTENSION_SCIENCE_v1

sha256sum A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz \
  | tee A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz.sha256

echo
echo "============================================================"
echo "A13-C0 AUTHOR EXECUTION COMPLETE"
echo
echo "UPLOAD THIS FILE:"
echo "A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz"
echo
echo "AND KEEP THIS HASH:"
cat A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_COMPLETE.tar.gz.sha256
echo "============================================================"

# ------------------------------------------------------------------
# CLEAN SHUTDOWN:
# Stop Qwen only if THIS script started it.
# ------------------------------------------------------------------

if [ "$STARTED_QWEN" -eq 1 ]; then
    echo
    echo "Stopping the Qwen server started by this script..."
    kill "$QWEN_PID" 2>/dev/null || true
    sleep 2

    if kill -0 "$QWEN_PID" 2>/dev/null; then
        echo "Qwen still exiting; server log remains preserved."
    else
        echo "Qwen server stopped."
    fi
else
    echo
    echo "Qwen was already running before this script, so it was left running."
fi
