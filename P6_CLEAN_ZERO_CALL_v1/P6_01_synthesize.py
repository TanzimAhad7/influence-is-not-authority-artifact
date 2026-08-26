#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from p6_common import sha256, load_json, load_jsonl, load_csv, write_csv, pct

def die(msg):
    print('P6 SYNTHESIS FAIL:',msg,file=sys.stderr)
    raise SystemExit(2)

def as_bool(x):
    return str(x).lower() in ('1','true','yes')

def verify_frozen_inputs(root,pkg,out,cfg):
    fpath=out/'P6_INPUT_FREEZE.json'
    if not fpath.is_file():
        die('missing PASS input freeze')
    freeze=load_json(fpath)
    if freeze.get('status')!='PASS':
        die('input freeze is not PASS')
    if freeze.get('config_sha256')!=sha256(pkg/'P6_CONFIG.json'):
        die('P6 config changed after input freeze')
    for pf in freeze['package_files']:
        p=pkg/pf['path']
        if not p.is_file() or sha256(p)!=pf['sha256']:
            die(f'package file changed after freeze: {pf["path"]}')
    for _,spec in cfg['inputs'].items():
        p=root/spec['path']
        if not p.is_file() or sha256(p)!=spec['sha256']:
            die(f'upstream input changed after freeze: {spec["path"]}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',required=True)
    ap.add_argument('--package-dir',required=True)
    ap.add_argument('--out-dir',required=True)
    a=ap.parse_args()
    root=Path(a.project_root).resolve()
    pkg=Path(a.package_dir).resolve()
    out=Path(a.out_dir).resolve()
    cfg=load_json(pkg/'P6_CONFIG.json')
    verify_frozen_inputs(root,pkg,out,cfg)

    r2=load_json(root/cfg['inputs']['r2a_results']['path'])
    a15=load_json(root/cfg['inputs']['a15a_results']['path'])
    awc=load_jsonl(root/cfg['inputs']['agentwatcher_controlled']['path'])
    awn=load_jsonl(root/cfg['inputs']['agentwatcher_natural']['path'])
    can=load_jsonl(root/cfg['inputs']['causalarmor_natural']['path'])
    attr_rows=load_jsonl(root/cfg['inputs']['attriguard_results']['path'])
    p0=load_json(root/cfg['inputs']['p0b3_analysis']['path'])
    cells=load_csv(root/cfg['inputs']['p3_cells']['path'])

    threshold_info={}
    for model,key in [('llama','r2a_llama_sweep'),('gemma','r2a_gemma_sweep')]:
        rows=load_csv(root/cfg['inputs'][key]['path'])
        intervals=[r for r in rows if r['threshold_label'].startswith('interval_')]
        nondeg=[r for r in rows if float(r['flag_rate']) not in (0.0,1.0)]
        interval_pos=sum(float(r['aivr_class'])>0 for r in intervals)
        nondeg_pos=sum(float(r['aivr_class'])>0 for r in nondeg)
        if (len(intervals),interval_pos)!=(95,95):
            die(f'{model}: expected 95/95 open interval regimes with AIVR>0')
        if (len(nondeg),nondeg_pos)!=(191,191):
            die(f'{model}: expected 191/191 nondegenerate rows with AIVR>0')
        threshold_info[model]={
            'open_interval_regimes_positive':interval_pos,
            'open_interval_regimes_total':len(intervals),
            'nondegenerate_rows_positive':nondeg_pos,
            'nondegenerate_rows_total':len(nondeg),
        }

    if len(awc)!=48 or sum(bool(r['detect_flag']) for r in awc)!=0:
        die('AgentWatcher controlled invariant mismatch')
    if len(awn)!=26 or sum(bool(r['detect_flag']) for r in awn)!=2:
        die('AgentWatcher natural invariant mismatch')
    if len(can)!=26 or sum(bool(r['CA_FLAG_0']) for r in can)!=16:
        die('CausalArmor natural invariant mismatch')
    if len(attr_rows)!=480 or sum(bool(r['blocked']) for r in attr_rows)!=0:
        die('AttriGuard final-decision invariant mismatch')
    strict=sum(r.get('judge_reason')=='shadow_match(strict)' for r in attr_rows)
    fuzzy=len(attr_rows)-strict
    if (strict,fuzzy)!=(441,39):
        die(f'AttriGuard route counts mismatch: {strict}/{fuzzy}')

    attack_rows=[]
    for _,spec in cfg['attack_runs'].items():
        rows=[]
        for p in sorted((root/spec['path']).rglob('*.json')):
            x=load_json(p)
            if x.get('attack_type')==spec['attack_type']:
                rows.append(x)
        attack_rows.append({
            'mechanism':'AgentWatcher',
            'attack':spec['attack_type'],
            'population':'frozen same-200 AgentDojo v1.2.2 pairs',
            'attack_success_n':sum(bool(x.get('security')) for x in rows),
            'n':len(rows),
            'ASR_percent':pct(sum(bool(x.get('security')) for x in rows),len(rows)),
            'utility_success_n':sum(bool(x.get('utility')) for x in rows),
            'utility_percent':pct(sum(bool(x.get('utility')) for x in rows),len(rows)),
            'claim_boundary':'Attack anchor only; P2 no-defense baseline is still required before calling low utility defense overhead.',
        })

    attack_rows.append({
        'mechanism':'CausalArmor',
        'attack':'AgentDojo primary attack population',
        'population':'949 attacks + 97 benign; v1.2.2 external calibration',
        'attack_success_n':round(p0['primary']['ASR_percent']/100*p0['population']['primary_attack']),
        'n':p0['population']['primary_attack'],
        'ASR_percent':p0['primary']['ASR_percent'],
        'utility_success_n':round(p0['primary']['UA_percent']/100*p0['population']['primary_attack']),
        'utility_percent':p0['primary']['UA_percent'],
        'claim_boundary':(
            f"{p0['primary']['disposition']}; benign utility {p0['primary']['BU_percent']:.2f}%; "
            f"nested629 ASR {p0['legacy_629_sensitivity']['ASR_percent']:.2f}% secondary; "
            f"serialization difference {p0['serialization_sensitivity']['absolute_activation_difference_pp']:.2f} pp PASS; "
            'not exact published reproduction.'
        ),
    })
    write_csv(out/'P6_ATTACK_ANCHORS.csv',attack_rows)

    auth_rows=[]
    for label in ['SPECIFIED','DELEGATED','PARTIAL','ALL']:
        if label=='ALL':
            ca=can; aw=awn
            a15_n=a15['eligible_decisions']; a15_k=a15['activated_decisions_tau0']
        else:
            ca=[r for r in can if r['label']==label]
            aw=[r for r in awn if r['label']==label]
            a15_n=a15['by_label'][label]['n_decisions']
            a15_k=a15['by_label'][label]['n_activated']
        ca_k=sum(bool(r['CA_FLAG_0']) for r in ca)
        aw_k=sum(bool(r['detect_flag']) for r in aw)
        auth_rows.append({
            'authorization':label,
            'population_scope':'historical original-26 A13-valid subset',
            'a15a_causal_support_activation_n':a15_k,
            'a15a_n':a15_n,
            'a15a_activation_percent':pct(a15_k,a15_n),
            'causalarmor_natural_flag_n':ca_k,
            'causalarmor_n':len(ca),
            'causalarmor_flag_percent':pct(ca_k,len(ca)),
            'agentwatcher_natural_flag_n':aw_k,
            'agentwatcher_n':len(aw),
            'agentwatcher_flag_percent':pct(aw_k,len(aw)),
            'claim_boundary':'Descriptive operating points on frozen original-26 subset; not corrected-29 prevalence.',
        })
    write_csv(out/'P6_AUTHORIZATION_STRATIFIED_BENIGN.csv',auth_rows)

    controlled=[]
    for model in ['llama','gemma']:
        s=r2['summary'][model]
        ti=threshold_info[model]
        controlled.append({
            'mechanism':f'CausalArmor-style thresholded causal-support scorer ({model})',
            'population':'A14-Minimal 24 exact-action-fixed bases',
            'metric':'AIVR at tau=0',
            'numerator':s['tau0']['aivr_class_n'],
            'denominator':24,
            'rate_percent':100*s['tau0']['aivr_class'],
            'secondary':(
                f"{ti['open_interval_regimes_positive']}/{ti['open_interval_regimes_total']} open nonconstant interval regimes and "
                f"{ti['nondegenerate_rows_positive']}/{ti['nondegenerate_rows_total']} all nondegenerate evaluated rows retain AIVR>0"
            ),
            'interpretation':'Threshold/operating point matters, but benign invariance failure is not a tau=0 artifact; attack sensitivity at alternative thresholds is untested here.',
        })
    controlled.append({
        'mechanism':'AgentWatcher FULL',
        'population':'A14-Minimal ECHO conditions, 24 bases × USER/TOOL provenance = 48',
        'metric':'benign flags','numerator':0,'denominator':48,'rate_percent':0.0,
        'secondary':'all 48 monitor parses valid',
        'interpretation':'Architecture does not convert the controlled benign provenance relocation into intervention.',
    })
    controlled.append({
        'mechanism':'AttriGuard',
        'population':'A14-Minimal 96 conditions × 5 repeats = 480',
        'metric':'final blocks','numerator':0,'denominator':480,'rate_percent':0.0,
        'secondary':f'{strict}/480 strict survival; {fuzzy}/480 fuzzy survival',
        'interpretation':'Final endpoint is invariant here; fuzzy survival is internal tolerance, not a false-positive count.',
    })
    write_csv(out/'P6_CONTROLLED_BENIGN_CONSISTENCY.csv',controlled)

    replay=[]
    hslot=[]
    model_specs=[('llama','p2b_llama','hslot_llama'),('gemma','p2b_gemma','hslot_gemma'),('qwen','p2b_qwen','hslot_qwen')]
    for m,ak,hk in model_specs:
        arm=load_json(root/cfg['inputs'][ak]['path'])
        hs=load_json(root/cfg['inputs'][hk]['path'])
        al=arm['action_local_gate']; ds=arm['downstream_continuation_gate']
        replay.append({
            'model':m,'model_id':arm['model_id'],'generations':arm['rows'],'decision_cells':26,'stability_repeats_per_cell':5,
            'instrument_valid':arm['instrument']['pass'],
            'action_local_success_n':round(al['overall_rate']*arm['rows']),'action_local_total':arm['rows'],'action_local_percent':100*al['overall_rate'],
            'downstream_success_n':round(ds['overall_rate']*arm['rows']),'downstream_total':arm['rows'],'downstream_percent':100*ds['overall_rate'],
            'disposition':arm['scientific_disposition'],
            'claim_boundary':'Baseline validity result on historical original-26 subset; no intervention authorized.',
        })
        c=hs['paired_contrasts']['OPEN_TEXT_minus_REFERENCE_IDENTITY']
        hslot.append({
            'model':m,'model_id':hs['model_id'],'contrast':'OPEN_TEXT - REFERENCE_IDENTITY','n_paired_decisions':c['n'],
            'mean':c['mean'],'ci95_low':c['ci95'][0],'ci95_high':c['ci95'][1],
            'instrument_valid':hs['instrument_valid_for_confirmatory_hslot'],
            'role':'Primary per-family H-SLOT contrast; do not treat 390 repeats as independent inference units.',
        })
    write_csv(out/'P6_REPLAY_EQUIVALENCE_MATRIX.csv',replay)
    write_csv(out/'P6_ARGUMENT_ROLE_HSLOT.csv',hslot)

    groups={True:[r for r in cells if as_bool(r['activated'])],False:[r for r in cells if not as_bool(r['activated'])]}
    sel=[]
    for activated,rs in groups.items():
        n=len(rs)
        action=sum(as_bool(r['action_majority']) for r in rs)
        down=sum(as_bool(r['downstream_majority']) for r in rs)
        mask=sum(as_bool(r['masking_majority']) for r in rs)
        sel.append({
            'selected_by_a15a_activation':activated,'model_decision_cells':n,
            'action_local_majority_pass_n':action,'action_local_majority_percent':pct(action,n),
            'downstream_majority_pass_n':down,'downstream_majority_percent':pct(down,n),
            'masking_majority_n':mask,'masking_majority_percent':pct(mask,n),
            'claim_boundary':'Post-hoc, composition-confounded selected-population behavior; mechanism evidence only, not a causal activation effect.',
        })
    write_csv(out/'P6_SELECTED_POPULATION_BEHAVIOR.csv',sel)

    ladder=[
        {'level':1,'layer':'interface','default_rule':'response must be parseable under the frozen interface','security_note':'instrument validity precedes outcome comparison'},
        {'level':2,'layer':'tool identity','default_rule':'exact target tool/function identity unless threat model explicitly permits substitution','security_note':'wrong tool is action-local divergence'},
        {'level':3,'layer':'argument / typed equivalence','default_rule':'identity/opaque fields exact; structured fields canonicalize only under explicit API semantics; open text threat-model-aware','security_note':'do not silently semantic-normalize security-relevant content'},
        {'level':4,'layer':'runtime / execution','default_rule':'validate schema and executability in the pinned environment','security_note':'parseable text is not necessarily executable action'},
        {'level':5,'layer':'deterministic effect','default_rule':'compare security-relevant state/effect under task-specific oracle','security_note':'effect can diverge even when function identity matches'},
        {'level':6,'layer':'downstream utility','default_rule':'evaluate task completion separately from immediate action/effect fidelity','security_note':'success can mask local divergence'},
        {'level':7,'layer':'final security verdict','default_rule':'apply architecture-specific security decision','security_note':'causal dependence alone is not authority'},
    ]
    write_csv(out/'P6_EQUIVALENCE_LADDER.csv',ladder)

    claims=[
        {'claim':'A benign authorization-equivalent execution can produce attack-like causal-support behavior.','status':'SUPPORTED','evidence':'A14 exact-action-fixed causal diagnosis + R2A threshold robustness','boundary':'A14 carries causal claim; P6 only packages it.'},
        {'claim':'The same benign causal variation is universally converted into intervention.','status':'REJECTED','evidence':'AgentWatcher controlled 0/48; AttriGuard 0/480 final blocks','boundary':'Architecture is a distinct layer.'},
        {'claim':'Alternative thresholding alone solves the security problem.','status':'NOT SUPPORTED','evidence':'R2A 95/95 open nonconstant regimes retain AIVR>0; attack sensitivity at those thresholds not evaluated','boundary':'Do not optimize threshold post hoc.'},
        {'claim':'Replay/equivalence validity is an operating condition for counterfactual security evaluation.','status':'SUPPORTED','evidence':'Corrected P2b: action-local 38.5/26.9/42.3% vs downstream 65.4/57.7/73.1%; instruments valid','boundary':'Not a universal replay-defense error rate.'},
        {'claim':'Downstream utility alone establishes immediate action/effect fidelity.','status':'REJECTED','evidence':'Corrected P2b + selected-population masking','boundary':'23/78 masking cells is cell-level; selected-pop differences are post-hoc.'},
        {'claim':'AttriGuard fuzzy routes are final false positives.','status':'REJECTED','evidence':'480/480 final ALLOW; 441 strict + 39 fuzzy internal survival','boundary':'Route is internal tolerance, not endpoint error.'},
        {'claim':'P0b-3 exactly reproduces the published CausalArmor attack table.','status':'REJECTED','evidence':f"Primary BU {p0['primary']['BU_percent']:.2f}%, UA {p0['primary']['UA_percent']:.2f}%, ASR {p0['primary']['ASR_percent']:.2f}% => SAME_EXTERNAL_REGIME; suite heterogeneity",'boundary':'External-regime calibration only; disclose nested629 and serialization qualification.'},
    ]
    write_csv(out/'P6_CLAIM_LEDGER.csv',claims)

    master=[]
    for r in controlled:
        master.append({
            'dimension':'authorization consistency / controlled benign','system':r['mechanism'],'population':r['population'],
            'headline':f"{r['numerator']}/{r['denominator']} ({r['rate_percent']:.1f}%) {r['metric']}",
            'interpretation':r['interpretation'],
        })
    master.extend([
        {'dimension':'benign operating point','system':'A15a CausalArmor-style activation','population':'historical original-26 natural subset','headline':f"{a15['activated_decisions_tau0']}/{a15['eligible_decisions']} ({100*a15['decision_activation_rate_tau0']:.1f}%) activated at tau=0",'interpretation':'Signal reaches expensive sanitizer stage; not end-to-end task harm.'},
        {'dimension':'architecture localization','system':'CausalArmor-style vs AgentWatcher FULL','population':'historical original-26 natural subset','headline':'16/26 vs 2/26 benign flags','interpretation':'Same natural cases produce different intervention behavior across architectures.'},
        {'dimension':'malicious discrimination anchor','system':'AgentWatcher','population':'same frozen 200-pair attacks','headline':f"important_instructions {attack_rows[0]['attack_success_n']}/200; tool_knowledge {attack_rows[1]['attack_success_n']}/200 ASR",'interpretation':'Strong attack anchor; utility attribution awaits P2 no-defense baseline.'},
        {'dimension':'external calibration','system':'CausalArmor P0b-3','population':'97 benign + 949 primary attacks','headline':f"BU {p0['primary']['BU_percent']:.2f}%; UA {p0['primary']['UA_percent']:.2f}%; ASR {p0['primary']['ASR_percent']:.2f}%",'interpretation':'SAME_EXTERNAL_REGIME with population/suite qualification.'},
        {'dimension':'replay / equivalence validity','system':'corrected P2b, 3 models','population':'78 model×decision cells × 5 stability repeats','headline':'action-local 38.5/26.9/42.3% vs downstream 65.4/57.7/73.1%','interpretation':'Downstream success can hide immediate action/effect divergence.'},
        {'dimension':'argument-role localization','system':'corrected P2b H-SLOT','population':'paired decision-level contrasts','headline':'OPEN_TEXT − REFERENCE_IDENTITY negative in all 3 models','interpretation':'Where equivalence breaks is structured by argument role; exact orbit portability is not claimed.'},
        {'dimension':'selected-population behavior','system':'P3 post-hoc','population':'78 model×decision cells','headline':'activated vs control masking 20/54 vs 3/24','interpretation':'Mechanism evidence only; post-hoc and composition-confounded.'},
    ])
    write_csv(out/'P6_MASTER_EVALUATION_VECTOR.csv',master)

    rows_svg=[
        ('Causal-support invariance','R2A','20/24 Llama; 18/24 Gemma AIVR @ τ=0'),
        ('Benign operating point','A15a','18/26 natural decisions activate sanitizer stage'),
        ('Architecture boundary','AgentWatcher / AttriGuard','0/48 controlled AW; 0/480 AttriGuard final blocks'),
        ('Natural architecture boundary','CA-style vs AgentWatcher','16/26 vs 2/26 benign flags'),
        ('Malicious anchors','AgentWatcher','1/200 and 0/200 ASR'),
        ('External calibration','CausalArmor P0b-3','BU 51.55% · UA 40.67% · ASR 3.37%'),
        ('Replay validity','Corrected P2b','action-local < downstream across all 3 models'),
        ('Argument role','H-SLOT','OPEN_TEXT − REFERENCE_IDENTITY < 0 in 3/3'),
    ]
    W=1200; H=110+len(rows_svg)*78
    esc=lambda s:s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.t{font-size:28px;font-weight:700}.h{font-size:18px;font-weight:700}.b{font-size:17px}.n{font-size:14px;fill:#444}</style>',
        '<text x="30" y="42" class="t">P6: authorization consistency × operating point × discrimination × replay validity</text>',
        '<text x="30" y="72" class="n">Synthesis only · zero model calls · no universal scalar · natural downstream rows remain historical original-26 subset</text>',
    ]
    y=105
    for dim,sysn,val in rows_svg:
        parts.extend([
            f'<rect x="30" y="{y}" width="1140" height="60" rx="8" fill="none" stroke="#777"/>',
            f'<text x="48" y="{y+24}" class="h">{esc(dim)}</text>',
            f'<text x="350" y="{y+24}" class="b">{esc(sysn)}</text>',
            f'<text x="650" y="{y+24}" class="b">{esc(val)}</text>',
        ])
        y+=78
    parts.append('</svg>')
    (out/'P6_EVALUATION_FRAMEWORK.svg').write_text('\n'.join(parts)+'\n')

    synthesis={
        'schema':'P6_CLEAN_SYNTHESIS_V1_2026-08-12','status':'COMPLETE','scientific_model_calls':0,
        'role':'evaluation-vector synthesis; not a fifth contribution or universal scalar',
        'population_lineage':cfg['population_lineage'],
        'r2a_threshold_resolution':threshold_info,
        'controlled':{'agentwatcher_flags':[0,48],'attriguard_final_blocks':[0,480],'attriguard_routes':{'strict':strict,'fuzzy':fuzzy}},
        'natural_original26':{'a15a_activation':[a15['activated_decisions_tau0'],a15['eligible_decisions']],'causalarmor_flags':[sum(bool(r['CA_FLAG_0']) for r in can),26],'agentwatcher_flags':[sum(bool(r['detect_flag']) for r in awn),26]},
        'attack_anchors':attack_rows,'replay_rows':replay,'hslot_rows':hslot,'selected_population':sel,
        'hard_boundaries':cfg['hard_boundaries'],
    }
    (out/'P6_SYNTHESIS.json').write_text(json.dumps(synthesis,indent=2,sort_keys=True)+'\n')

    md=f"""# P6 — Consistency × Discrimination × Replay/Equivalence Packaging

**Status:** COMPLETE / ZERO MODEL CALLS / SYNTHESIS ONLY

## Reviewer-facing evaluation vector

1. **Authorization consistency / controlled benign:** at `tau=0`, AIVR is `20/24` (Llama) and `18/24` (Gemma). All `95/95` open nonconstant interval regimes retain AIVR>0 for each scorer; equivalently all `191/191` nondegenerate evaluated sweep rows (breakpoints + intervals + tau0) retain AIVR>0. This is benign threshold robustness, not an attack-sensitivity frontier.
2. **Benign operating point:** A15a activates on `{a15['activated_decisions_tau0']}/{a15['eligible_decisions']} = {100*a15['decision_activation_rate_tau0']:.1f}%` of the historical original-26 natural decisions; SPECIFIED `{a15['by_label']['SPECIFIED']['n_activated']}/{a15['by_label']['SPECIFIED']['n_decisions']}`, DELEGATED `{a15['by_label']['DELEGATED']['n_activated']}/{a15['by_label']['DELEGATED']['n_decisions']}`, PARTIAL `{a15['by_label']['PARTIAL']['n_activated']}/{a15['by_label']['PARTIAL']['n_decisions']}`.
3. **Architecture boundary:** AgentWatcher flags `0/48` controlled A14 ECHO conditions and `2/26` natural benign decisions, while the paired CausalArmor-style natural operating point is `16/26`. AttriGuard produces `0/480` final blocks; `441/480` survive strict matching and `39/480` use fuzzy survival.
4. **Malicious discrimination anchors:** AgentWatcher ASR is `{attack_rows[0]['attack_success_n']}/200` on `important_instructions` and `{attack_rows[1]['attack_success_n']}/200` on `tool_knowledge`. Utility is `{attack_rows[0]['utility_success_n']}/200` and `{attack_rows[1]['utility_success_n']}/200`, respectively; **P2 no-defense baseline remains required before calling this utility loss defense overhead.**
5. **External calibration:** P0b-3 primary `BU={p0['primary']['BU_percent']:.2f}%`, `UA={p0['primary']['UA_percent']:.2f}%`, `ASR={p0['primary']['ASR_percent']:.2f}%` → `{p0['primary']['disposition']}`. Nested629 ASR `{p0['legacy_629_sensitivity']['ASR_percent']:.2f}%` is secondary; serialization difference `{p0['serialization_sensitivity']['absolute_activation_difference_pp']:.2f} pp` passes the frozen sensitivity gate.
6. **Replay/equivalence validity:** corrected P2b instruments are valid, but action-local preservation is `50/130`, `35/130`, `55/130` (Llama/Gemma/Qwen) while downstream utility is `85/130`, `75/130`, `95/130`. These are `78` model×decision cells with five stability repeats, not 390 independent samples.
7. **Argument-role localization:** OPEN_TEXT − REFERENCE_IDENTITY is negative in all three corrected H-SLOT arms: Llama `{hslot[0]['mean']:+.4f}` CI `[{hslot[0]['ci95_low']:+.4f},{hslot[0]['ci95_high']:+.4f}]`; Gemma `{hslot[1]['mean']:+.4f}` CI `[{hslot[1]['ci95_low']:+.4f},{hslot[1]['ci95_high']:+.4f}]`; Qwen `{hslot[2]['mean']:+.4f}` CI `[{hslot[2]['ci95_low']:+.4f},{hslot[2]['ci95_high']:+.4f}]`.
8. **Selected-population behavior:** post-hoc P3 shows downstream-PASS/action-local-FAIL masking `20/54` among A15a-activated model×decision cells vs `3/24` controls. This is mechanism evidence, **not** a causal activation effect.

## Paper role

P6 does not add a fifth contribution and does not propose a universal scalar. It makes the existing systems story reviewer-usable:

`authorization consistency × benign operating point × malicious discrimination × replay/equivalence validity × selected-population behavior`.

The evaluation ladder is:

`interface → tool identity → typed argument equivalence → runtime/execution → deterministic effect → downstream utility → final security verdict`.

## Population lineage

The A15a, AgentWatcher-natural, and corrected P2b rows above are frozen studies of the **historical original-26 A13-valid subset**. A13-C0 later corrected the ecological census to 29 valid decisions; P6 does not retroactively relabel these completed downstream studies as corrected-29 prevalence.

## Hard claim boundaries

- Causal dependence is not authority; P6 packages evidence for that story but A14 remains the causal centerpiece.
- Do not infer that alternative thresholds preserve attack sensitivity from R2A alone.
- Do not call AttriGuard's 39 fuzzy-survival routes false positives.
- Do not call AgentWatcher attack utility loss defense overhead until P2 supplies the same-200 no-defense baseline.
- Do not turn P2b mismatch into a universal replay-defense error rate.
- Do not treat the selected-population masking contrast as confirmatory or causal.
- Do not claim P0b-3 is an exact reproduction of the published CausalArmor table.
"""
    (out/'P6_SUMMARY.md').write_text(md)
    print('P6 CLEAN SYNTHESIS COMPLETE')
    print('master_rows=',len(master),'controlled_rows=',len(controlled),'attack_rows=',len(attack_rows),'replay_rows=',len(replay),'hslot_rows=',len(hslot))
    print('attriguard_routes=',strict,fuzzy)

if __name__=='__main__':
    main()
