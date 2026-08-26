#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, html, json, math, random, statistics
from collections import Counter, defaultdict
from pathlib import Path


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_jsonl(p: Path):
    out = []
    with p.open(encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:
                raise RuntimeError(f'JSONL parse failure {p}:{i}: {e}')
    return out


def mean(xs):
    return statistics.mean(xs) if xs else None


def quantile(vals, q):
    if not vals:
        return None
    vals = sorted(vals)
    if len(vals) == 1:
        return vals[0]
    pos = q * (len(vals) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return vals[lo]
    w = pos - lo
    return vals[lo] * (1 - w) + vals[hi] * w


def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = r
        i = j
    return ranks


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return None if den == 0 else sum(a*b for a, b in zip(dx, dy)) / den


def spearman(xs, ys):
    return pearson(rankdata(xs), rankdata(ys)) if len(xs) >= 2 else None


def per_task_label_values(records, field):
    buckets = defaultdict(lambda: defaultdict(list))
    for r in records:
        if not r.get('primary_valid') or r.get('development'):
            continue
        lab = r.get('label')
        if lab not in {'SPECIFIED', 'DELEGATED'}:
            continue
        v = r.get(field)
        if isinstance(v, bool):
            v = float(v)
        if v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue
        if math.isfinite(v):
            buckets[r['task_key']][lab].append(v)
    return {tk: {lab: mean(vs) for lab, vs in d.items()} for tk, d in buckets.items()}


def clustered_contrast(records, field, B, seed):
    tv = per_task_label_values(records, field)
    tids = sorted(tv)

    def calc(sample):
        spec, deleg = [], []
        for tk in sample:
            if 'SPECIFIED' in tv[tk]:
                spec.append(tv[tk]['SPECIFIED'])
            if 'DELEGATED' in tv[tk]:
                deleg.append(tv[tk]['DELEGATED'])
        if not spec or not deleg:
            return None
        return {
            'specified_mean': mean(spec),
            'delegated_mean': mean(deleg),
            'difference': mean(spec) - mean(deleg),
            'n_specified_tasks': len(spec),
            'n_delegated_tasks': len(deleg)
        }

    point = calc(tids)
    rng = random.Random(seed + sum(map(ord, field)))
    draws = []
    for _ in range(B):
        sample = [tids[rng.randrange(len(tids))] for __ in tids]
        z = calc(sample)
        if z is not None:
            draws.append(z['difference'])
    point['ci95'] = [quantile(draws, .025), quantile(draws, .975)]
    point['bootstrap_valid_draws'] = len(draws)
    return point


def write_csv(p: Path, rows):
    rows = list(rows)
    if not rows:
        p.write_text('')
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def assert_close(a, b, tol=1e-12, label='value'):
    if abs(float(a) - float(b)) > tol:
        raise RuntimeError(f'{label} mismatch: expected {b}, got {a}')


def svg_forest(path: Path, headline, loso, loto):
    width = 1050
    left = 330
    right = 70
    x0, x1 = -0.15, 1.05
    plot_w = width - left - right
    rows = [('Corrected-29 frozen primary', headline['difference'], headline['ci95'][0], headline['ci95'][1], 'primary')]
    for r in loso:
        rows.append((f"Leave out suite: {r['excluded_suite']}", r['H_difference'], r['H_ci_low'], r['H_ci_high'], 'suite'))
    row_h = 42
    height = 160 + row_h * len(rows) + 120
    def X(v):
        return left + (v - x0) / (x1 - x0) * plot_w
    def esc(s): return html.escape(str(s))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
             '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111} .small{font-size:13px}.lab{font-size:15px}.title{font-size:21px;font-weight:700}.axis{stroke:#333;stroke-width:1}.ci{stroke:#111;stroke-width:2}.zero{stroke:#777;stroke-width:1;stroke-dasharray:5 5}</style>',
             '<text x="20" y="32" class="title">P3-C0 corrected-29 A13 influence refresh</text>',
             '<text x="20" y="55" class="small">H = task-level SPECIFIED − DELEGATED; primary row is frozen A13-C0, deletion rows are post-hoc sensitivity.</text>']
    y_axis = 95
    parts.append(f'<line x1="{X(0):.2f}" x2="{X(0):.2f}" y1="{y_axis-10}" y2="{height-75}" class="zero"/>')
    for t in [-0.1,0,0.2,0.4,0.6,0.8,1.0]:
        x = X(t)
        parts.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{height-70}" y2="{height-64}" class="axis"/>')
        parts.append(f'<text x="{x:.2f}" y="{height-45}" text-anchor="middle" class="small">{t:+.1f}</text>')
    for i,(lab,est,lo,hi,kind) in enumerate(rows):
        y = 105 + i*row_h
        parts.append(f'<text x="20" y="{y+5}" class="lab">{esc(lab)}</text>')
        parts.append(f'<line x1="{X(lo):.2f}" x2="{X(hi):.2f}" y1="{y}" y2="{y}" class="ci"/>')
        parts.append(f'<line x1="{X(lo):.2f}" x2="{X(lo):.2f}" y1="{y-5}" y2="{y+5}" class="ci"/>')
        parts.append(f'<line x1="{X(hi):.2f}" x2="{X(hi):.2f}" y1="{y-5}" y2="{y+5}" class="ci"/>')
        if kind == 'primary':
            x=X(est); parts.append(f'<polygon points="{x-8:.2f},{y} {x:.2f},{y-8} {x+8:.2f},{y} {x:.2f},{y+8}" fill="#111"/>')
        else:
            parts.append(f'<circle cx="{X(est):.2f}" cy="{y}" r="5" fill="#111"/>')
        parts.append(f'<text x="{width-20}" y="{y+5}" text-anchor="end" class="small">{est:+.3f} [{lo:+.3f}, {hi:+.3f}]</text>')
    rug_y = 105 + len(rows)*row_h + 32
    vals = [r['H_difference'] for r in loto]
    parts.append(f'<text x="20" y="{rug_y+5}" class="lab">Leave-one-task point estimates (n={len(vals)})</text>')
    parts.append(f'<line x1="{X(min(vals)):.2f}" x2="{X(max(vals)):.2f}" y1="{rug_y}" y2="{rug_y}" class="ci"/>')
    for v in vals:
        parts.append(f'<line x1="{X(v):.2f}" x2="{X(v):.2f}" y1="{rug_y-7}" y2="{rug_y+7}" stroke="#111" stroke-width="1"/>')
    parts.append(f'<text x="{width-20}" y="{rug_y+5}" text-anchor="end" class="small">range {min(vals):+.3f} to {max(vals):+.3f}</text>')
    parts.append(f'<line x1="{left}" x2="{width-right}" y1="{height-70}" y2="{height-70}" class="axis"/>')
    parts.append(f'<text x="{(left+width-right)/2:.2f}" y="{height-15}" text-anchor="middle" class="lab">H difference (SPECIFIED − DELEGATED)</text>')
    parts.append('</svg>')
    path.write_text('\n'.join(parts) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    out = Path(args.out_dir).resolve()
    freeze_p = out / 'P3_C0_ANALYSIS_FREEZE.json'
    if not freeze_p.exists():
        raise SystemExit('FATAL run P3_C0_00_freeze.py first')
    fr = json.loads(freeze_p.read_text())
    cfg = fr['config']
    for name, d in fr['input_files'].items():
        p = Path(d['path'])
        if not p.exists() or sha256(p) != d['sha256']:
            raise SystemExit(f'FATAL frozen input drift: {name} {p}')

    ledger_p = root / cfg['expected_inputs']['combined_73_ledger']['relative_path']
    result_p = root / cfg['expected_inputs']['extension_result']['relative_path']
    rows = load_jsonl(ledger_p)
    ext = json.loads(result_p.read_text())
    valid = [r for r in rows if r.get('primary_valid') and not r.get('development')]

    exp = cfg['expected_population']
    labels = Counter(r['label'] for r in valid)
    if len(rows) != exp['decision_rows'] or len(valid) != exp['primary_valid_decisions'] or len({r['task_key'] for r in valid}) != exp['primary_valid_tasks'] or dict(labels) != exp['labels']:
        raise RuntimeError(f'Population mismatch rows={len(rows)} valid={len(valid)} tasks={len({r["task_key"] for r in valid})} labels={dict(labels)}')

    frozen = ext['coverage_corrected_primary']['primary_H_mean_del']
    for k in ['specified_mean','delegated_mean','difference']:
        assert_close(frozen[k], cfg['frozen_headline_H'][k], label=f'frozen headline {k}')
    for i in [0,1]:
        assert_close(frozen['ci95'][i], cfg['frozen_headline_H']['ci95'][i], label=f'frozen headline ci[{i}]')

    B = int(cfg['bootstrap_repetitions'])
    seed = int(cfg['bootstrap_seed'])
    recomputed_H = clustered_contrast(valid, 'H_mean_del', B, seed)
    recomputed_M = clustered_contrast(valid, 'M_del', B, seed)

    loso=[]
    for suite in sorted({r['suite'] for r in valid}):
        rr=[r for r in valid if r['suite'] != suite]
        h=clustered_contrast(rr,'H_mean_del',B,seed)
        m=clustered_contrast(rr,'M_del',B,seed)
        loso.append({'excluded_suite':suite,'n_valid_decisions_remaining':len(rr),'n_tasks_remaining':len({r["task_key"] for r in rr}),
                     'H_difference':h['difference'],'H_ci_low':h['ci95'][0],'H_ci_high':h['ci95'][1],
                     'M_difference':m['difference'],'M_ci_low':m['ci95'][0],'M_ci_high':m['ci95'][1]})

    loto=[]
    Bt=int(cfg['leave_one_task_bootstrap_repetitions'])
    for tk in sorted({r['task_key'] for r in valid}):
        rr=[r for r in valid if r['task_key'] != tk]
        h=clustered_contrast(rr,'H_mean_del',Bt,seed)
        loto.append({'excluded_task':tk,'suite':next(r['suite'] for r in valid if r['task_key']==tk),
                     'n_valid_decisions_remaining':len(rr),'H_difference':h['difference'],'H_ci_low':h['ci95'][0],'H_ci_high':h['ci95'][1]})

    taskagg=[]
    for tk in sorted({r['task_key'] for r in valid}):
        rs=[r for r in valid if r['task_key']==tk]
        taskagg.append({'task_key':tk,'suite':rs[0]['suite'],
                        'specified_fraction':mean([float(r['specified_fraction']) for r in rs if r.get('specified_fraction') is not None]),
                        'n_eligible_tool_spans':mean([float(r.get('n_eligible_tool_spans',0)) for r in rs]),
                        'H_mean_del':mean([float(bool(r['H_mean_del'])) for r in rs]),
                        'M_del':mean([float(r['M_del']) for r in rs]),
                        'labels':','.join(sorted({r['label'] for r in rs}))})
    xs=[r['n_eligible_tool_spans'] for r in taskagg]
    span_diag={'n_tasks':len(taskagg),
               'spans_vs_H_pearson':pearson(xs,[r['H_mean_del'] for r in taskagg]),
               'spans_vs_H_spearman':spearman(xs,[r['H_mean_del'] for r in taskagg]),
               'spans_vs_M_pearson':pearson(xs,[r['M_del'] for r in taskagg]),
               'spans_vs_M_spearman':spearman(xs,[r['M_del'] for r in taskagg]),
               'spans_vs_specified_fraction_pearson':pearson(xs,[r['specified_fraction'] for r in taskagg]),
               'spans_vs_specified_fraction_spearman':spearman(xs,[r['specified_fraction'] for r in taskagg])}

    result={'schema':'P3_C0_CORRECTED29_REFRESH_RESULT_V1','scientific_model_calls':0,
            'status':'POSTHOC_PRESENTATION_AND_INFLUENCE_REFRESH','frozen_A13_C0_headline':frozen,
            'independent_recompute_under_P3_seed':{'H':recomputed_H,'M':recomputed_M},
            'population':{'rows':len(rows),'valid_decisions':len(valid),'valid_tasks':len({r['task_key'] for r in valid}),'labels':dict(labels)},
            'leave_one_suite_out':loso,'leave_one_task_out':loto,'task_span_diagnostics':span_diag,
            'claim_boundary':'The frozen A13-C0 headline remains authoritative. Deletion analyses are post-hoc sensitivity/influence only.'}
    (out/'P3_C0_REFRESH.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    write_csv(out/'P3_C0_LEAVE_ONE_SUITE_OUT.csv',loso)
    write_csv(out/'P3_C0_LEAVE_ONE_TASK_OUT.csv',loto)
    write_csv(out/'P3_C0_TASK_SPAN_DIAGNOSTICS.csv',taskagg)
    svg_forest(out/'P3_C0_FOREST.svg', frozen, loso, loto)

    summary = f'''# P3-C0 corrected-29 zero-call refresh\n\n**Status:** COMPLETE / POST-HOC PRESENTATION + INFLUENCE REFRESH / 0 scientific model calls.\n\n## Frozen A13-C0 headline — unchanged\n\n- SPECIFIED H: `{frozen['specified_mean']:.4f}`\n- DELEGATED H: `{frozen['delegated_mean']:.4f}`\n- difference: `{frozen['difference']:+.4f}`\n- frozen 95% CI: `[{frozen['ci95'][0]:+.4f}, {frozen['ci95'][1]:+.4f}]`\n\n## Corrected-29 influence refresh\n\n- valid decisions: `{len(valid)}` across `{len({r['task_key'] for r in valid})}` tasks\n- leave-one-suite H difference range: `[{min(r['H_difference'] for r in loso):+.4f}, {max(r['H_difference'] for r in loso):+.4f}]`\n- leave-one-task H difference range: `[{min(r['H_difference'] for r in loto):+.4f}, {max(r['H_difference'] for r in loto):+.4f}]`\n- eligible-span count vs task-level H: Pearson `{span_diag['spans_vs_H_pearson']:+.4f}`, Spearman `{span_diag['spans_vs_H_spearman']:+.4f}`\n\nThese deletion analyses are post-hoc sensitivity/influence diagnostics. They do not replace the frozen A13-C0 primary result.\n'''
    (out/'P3_C0_SUMMARY.md').write_text(summary)
    print('P3-C0 REFRESH PASS')
    print(summary)

if __name__ == '__main__':
    main()
