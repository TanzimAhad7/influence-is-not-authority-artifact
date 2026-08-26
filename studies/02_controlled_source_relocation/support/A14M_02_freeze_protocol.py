#!/usr/bin/env python3
"""A14-MINIMAL step 02: final pre-outcome protocol freeze. NO scorer calls."""
from __future__ import annotations
import argparse
from pathlib import Path
from a14m_common import *

SOURCE_FILES=[
    'a14m_common.py','A14M_00_prepare_draft.py','A14M_01_human_audit_cli.py',
    'A14M_01b_base_quartet_audit_cli.py','A14M_02_freeze_protocol.py',
    'A14M_03_score.py','A14M_04_analyze.py','A14M_PROTOCOL_SPEC.md',
    'PREFREEZE_AMENDMENT_01_BASE_QUARTET_AUDIT.md'
]
CORPUS_FILES=[
    'base_instances.json','contexts/structured_contexts.jsonl','authorization_equivalence_graph.jsonl',
    'mechanical_checks.jsonl','component_registry.jsonl','lineage_graph.jsonl','contexts/token_maps.jsonl',
    'completion_token_semantics.jsonl','neutral_replacements.jsonl','scoring_plan_llama.jsonl',
    'scoring_plan_gemma.jsonl','prediction_ledger.json','human_equivalence_audit_TEMPLATE.jsonl',
    'human_equivalence_audit.jsonl','human_base_quartet_audit_TEMPLATE.jsonl',
    'human_base_quartet_audit.jsonl','PREFREEZE_SUMMARY.json'
]


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='.'); args=ap.parse_args()
    root=project_root_from_args(args); out=a14_dir(root)
    p=out/'protocol.json'
    if p.exists():
        old=read_json(p); print(f"[A14M-02] already frozen: {old.get('protocol_hash')}"); return
    forbidden=['scorer_llama/condition_scores.jsonl','scorer_gemma/condition_scores.jsonl','analysis/results.json']
    bad=[x for x in forbidden if (out/x).exists() and (out/x).stat().st_size>0]
    if bad: raise SystemExit(f'FATAL outcomes exist before freeze: {bad}')

    pair_audit=read_jsonl(out/'human_equivalence_audit.jsonl')
    if len(pair_audit)!=16 or any(r.get('human_auth_equivalent') is not True for r in pair_audit):
        raise SystemExit('FATAL pairwise human audit must contain exactly 16/16 TRUE judgments before freeze')

    base_audit=read_jsonl(out/'human_base_quartet_audit.jsonl')
    if len(base_audit)!=24 or any(r.get('human_all_four_authorization_equivalent') is not True for r in base_audit):
        raise SystemExit('FATAL base quartet human audit must contain exactly 24/24 TRUE judgments before freeze')
    if len({r.get('base_id') for r in base_audit}) != 24:
        raise SystemExit('FATAL base quartet audit must cover 24 unique bases')

    summary=read_json(out/'PREFREEZE_SUMMARY.json')
    if summary.get('n_conditions')!=96 or summary.get('n_bases')!=24 or not summary.get('all_four_cells_prompt_token_matched_per_base'):
        raise SystemExit('FATAL prefreeze summary invariants failed')

    missing_sources=[f for f in SOURCE_FILES if not (root/f).exists()]
    if missing_sources: raise SystemExit(f'FATAL missing freeze source/doc files: {missing_sources}')
    missing_corpus=[f for f in CORPUS_FILES if not (out/f).exists()]
    if missing_corpus: raise SystemExit(f'FATAL missing freeze corpus/audit files: {missing_corpus}')

    source_hashes={f:sha256_file(root/f) for f in SOURCE_FILES}
    corpus_hashes={f:sha256_file(out/f) for f in CORPUS_FILES}
    protocol={
        'schema_version':SCHEMA_VERSION,'status':'FROZEN_PRE_OUTCOME','frozen_at_utc':now_utc(),
        'study':'A14 minimal authorization-invariance factorial: P1 provenance x P3 descendant redundancy',
        'paper_target':'USENIX Security main conference',
        'n_bases':24,'n_conditions':96,'design':'2x2 within-base factorial',
        'factors':{'provenance':['USER_ID','TOOL_ID'],'descendant':['SHAM','ECHO']},
        'primary_scorer':DEFAULT_SCORER,'source_fidelity_scorer':DEFAULT_SOURCE_FIDELITY_SCORER,
        'primary_tokenizer':summary['tokenizer'],
        'primary_estimands':read_json(out/'prediction_ledger.json')['primary_estimands'],
        'secondary_mechanistic_estimands':read_json(out/'prediction_ledger.json')['secondary_mechanistic_estimands'],
        'inference':read_json(out/'prediction_ledger.json')['inference'],
        'intervention':{'primary':'true component deletion','robustness':'Llama-token-count-matched neutral replacement'},
        'authorization_contract':{
            'every cell':'ALLOW','same_policy_hash_within_base':True,'same_exact_target_action_within_base':True,
            'pairwise_human_audit':'16/16 stratified factor-edge judgments TRUE',
            'base_quartet_human_audit':'24/24 bases TRUE; all 96 cells human-reviewed in four-cell context',
            'human_decision_maker':'author',
            'AI_assistance':'advisory deliberation only; final pass/fail judgments made by human author',
        },
        'prefreeze_amendments':[
            'Added exhaustive 24-base four-cell construct audit after reviewer-defensibility review, before final freeze and before any A14 scorer outcome. No scientific condition, estimand, scorer plan, or prediction was changed.'
        ],
        'scoring_plan_rows':{'llama':summary['llama_scoring_plan_rows'],'gemma':summary['gemma_scoring_plan_rows']},
        'source_hashes':source_hashes,'corpus_hashes':corpus_hashes,
        'claim_guardrails':[
            'A14M is prospective with respect to all A14 scoring outcomes; earlier large A14 designs had zero scorer outcomes.',
            'P1/P3 mechanisms were motivated before this freeze by A13/R2/R3 and A15a consequence evidence.',
            'A14M does not preregister the project from inception and does not make A12 confirmatory.',
            'Similar P1 and P3 effects do not prove mechanistic identity; interaction is a diagnostic of additivity/redundancy/synergy.',
            'Gemma is source-fidelity replication, not part of the primary Llama inference.',
            'The construct audit is author-conducted human review, not an independent annotation study.',
        ],
    }
    hview=dict(protocol); hview.pop('frozen_at_utc',None)
    protocol['protocol_hash']=sha256_text(stable_json(hview))
    dump_json(out/'source_hashes.json',source_hashes); dump_json(p,protocol)
    print(f"[A14M-02] FROZEN BEFORE A14 OUTCOMES: {protocol['protocol_hash']}")
    print(f"[A14M-02] conditions=96 llama_plan={summary['llama_scoring_plan_rows']} gemma_plan={summary['gemma_scoring_plan_rows']}")
    print('[A14M-02] human audit: 16/16 pairwise TRUE + 24/24 base quartets TRUE (96/96 cells covered)')
    print('[A14M-02] You may now start the scorer. Scientific corpus/code choices are locked.')

if __name__=='__main__': main()
