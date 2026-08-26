#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(pwd)}"
cd "$ROOT"
export A14M_TOKENIZER="${A14M_TOKENIZER:-meta-llama/Llama-3.3-70B-Instruct}"
python3 A14M_00_prepare_draft.py --project-root "$ROOT" --tokenizer "$A14M_TOKENIZER"
echo
echo "STOP: human audit and final freeze are separate. Do NOT start scorer yet."
