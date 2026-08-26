#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from p0b3_act_shadow_common import *

def main():
    ap=argparse.ArgumentParser(description='Freeze pre-specified P0b-3-ACT shadow-serialization benign/attack sensitivity. ZERO MODEL CALLS.')
    ap.add_argument('--project-root',default='.')
    ap.add_argument('--output-dir',default='P0B3_ACT_SHADOW_RUN_v1')
    a=ap.parse_args(); root=Path(a.project_root).resolve(); pkg=Path(__file__).resolve().parent
    inp=root/EXPECTED_INPUT_REL; out=root/a.output_dir; out.mkdir(parents=True,exist_ok=True)
    if not inp.is_file(): raise SystemExit(f'FATAL: missing {inp}')
    h=sha256_file(inp)
    if h!=EXPECTED_INPUT_SHA256: raise SystemExit(f'FATAL: input hash mismatch expected={EXPECTED_INPUT_SHA256} observed={h}')
    # IMPORTANT: validation checks schema/type/denominators only; it does NOT aggregate True shadow outcomes.
    v=validate(read_jsonl(inp),aggregate_shadow=False)
    freeze={
      'schema':SCHEMA,'stage':'FREEZE','created_utc':datetime.now(timezone.utc).isoformat(),
      'scientific_model_calls':0,'analysis_class':'PRE_SPECIFIED_SECONDARY_POST_HOC_DESCRIPTIVE_ZERO_CALL',
      'provenance_note':'Secondary shadow-serialization split was specified in canonical dossier v114 §1.6.8 before this split was inspected; this supplement freezes executable code before revealing benign/attack shadow outcomes.',
      'input':{'relative_path':str(EXPECTED_INPUT_REL),'sha256':h,'rows':v['total_events'],'unique_event_identities':v['unique_event_identities']},
      'frozen_denominators':v['denominators'],'frozen_total_privileged_decisions':v['total_events'],
      'endpoint':'SHADOW := shadow_any_flag (COMPLETION_PLUS_TOOL_CALL serialization)',
      'known_pre_split_overall_reconciliation':{'shadow_flagged_privileged_decisions':EXPECTED_OVERALL_SHADOW_FLAGGED,'privileged_decisions':EXPECTED_TOTAL_EVENTS},
      'reporting_lock':{'primary_secondary_outputs':['benign shadow flagged / benign privileged decisions','attack shadow flagged / attack privileged decisions'],'additional_descriptive':'attack_minus_benign_percentage_points','report_regardless_of_shape':True,'no_ci_no_pvalue':True,'no_threshold_tuning':True,'no_population_edits':True},
      'package_source_sha256':source_hashes(pkg),
    }
    fp=out/'P0B3_ACT_SHADOW_FREEZE.json'
    if fp.exists():
        old=json.loads(fp.read_text())
        for k in ('schema','stage','input','frozen_denominators','frozen_total_privileged_decisions','endpoint','known_pre_split_overall_reconciliation','reporting_lock','package_source_sha256'):
            if old.get(k)!=freeze.get(k): raise SystemExit(f'FATAL: existing freeze differs at {k}')
        print('[P0B3-ACT-SHADOW-00] EXISTING FREEZE VERIFIED'); print(f'[P0B3-ACT-SHADOW-00] denominators={v["denominators"]} total={v["total_events"]}'); print('[P0B3-ACT-SHADOW-00] NO shadow outcomes aggregated; ZERO model calls'); return 0
    write_json(fp,freeze)
    fsha=sha256_file(fp)
    (out/'P0B3_ACT_SHADOW_FREEZE.md').write_text(
      '# P0b-3-ACT shadow sensitivity pre-analysis freeze\n\n'
      f'- input SHA-256: `{h}`\n- denominators: `{v["denominators"]}`\n'
      '- endpoint: `shadow_any_flag` / `COMPLETION_PLUS_TOOL_CALL`\n'
      f'- known pre-split overall shadow activation from frozen P0b-3: `{EXPECTED_OVERALL_SHADOW_FLAGGED}/{EXPECTED_TOTAL_EVENTS}`\n'
      '- benign/attack shadow outcomes were not aggregated in this freeze stage\n'
      '- zero model calls; report regardless of shape; no CI/p-value/tuning\n'
      f'- freeze JSON SHA-256: `{fsha}`\n',encoding='utf-8')
    print('[P0B3-ACT-SHADOW-00] FREEZE PASS'); print(f'[P0B3-ACT-SHADOW-00] input_sha256={h}'); print(f'[P0B3-ACT-SHADOW-00] denominators={v["denominators"]} total={v["total_events"]}'); print(f'[P0B3-ACT-SHADOW-00] freeze_sha256={fsha}'); print('[P0B3-ACT-SHADOW-00] NO shadow outcomes aggregated; ZERO model calls'); return 0
if __name__=='__main__': raise SystemExit(main())
