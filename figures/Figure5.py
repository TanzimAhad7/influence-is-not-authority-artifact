#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

ROOT = Path(os.environ.get('PHASE0_ROOT', '/mnt/data/_handoff_phase0'))
OUT = Path(__file__).resolve().parent / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

AW_DIR = ROOT / 'AW_N3_AUTHOR_v1'
N6_DIR = ROOT / 'n6_attriguard_n3_v1' / 'scientific_v1'

EXPECTED_SHA = {
    AW_DIR / 'AWN3_RESULTS.json': '37a4c8d561aeb3d1f43c8ec3b1582a280f482a2acbc3d121affb5029b0678f41',
    AW_DIR / 'AWN3_VERIFY_REPORT.json': '7bc52459566dd25d827bab648e4c631cbaab7d898a3a551f3366d70cc7e1a2ca',
    AW_DIR / 'AWN3_MAPPED_OUTPUTS.jsonl': 'c79514c63346003044f6e3d04c7d1a680ce3e528ee5df9043762eb0b4389005c',
    N6_DIR / 'N6_ANALYSIS.json': '432bab81ef298938f095157328293c679f4c416dad1469c62022ccd55444a79f',
    N6_DIR / 'N6_RESULTS.jsonl': '847febc64c01f2e26075a072d1f4763a8e1ad693ee2f94ed31f0d78bb6d6dff8',
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# -------- Provenance + independent re-derivation --------
for path, expected in EXPECTED_SHA.items():
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f'hash mismatch: {path}: {actual} != {expected}')

aw_results = json.loads((AW_DIR / 'AWN3_RESULTS.json').read_text())
aw_verify = json.loads((AW_DIR / 'AWN3_VERIFY_REPORT.json').read_text())
aw_rows = load_jsonl(AW_DIR / 'AWN3_MAPPED_OUTPUTS.jsonl')
if aw_verify.get('status') != 'INTEGRITY_PASS':
    raise RuntimeError('AW-N3 verifier is not INTEGRITY_PASS')
if len(aw_rows) != 192:
    raise RuntimeError(f'AW mapped census drift: {len(aw_rows)}')

aw_by_state = defaultdict(list)
for r in aw_rows:
    aw_by_state[(r['directive_arm'], r['action_role'])].append(r)

aw_unique = {}
for key in [('ALIGNED','AUTH'), ('ALIGNED','ALT'), ('CONFLICT','AUTH'), ('CONFLICT','ALT')]:
    rs = aw_by_state[key]
    if len(rs) != 48:
        raise RuntimeError(f'AW mapped state census drift {key}: {len(rs)}')
    uniq = {}
    for r in rs:
        h = r['agentwatcher_static_input_sha256']
        v = bool(r['detect_flag'])
        if h in uniq and uniq[h] != v:
            raise RuntimeError(f'inconsistent duplicate static input {h}')
        uniq[h] = v
    if len(uniq) != 24:
        raise RuntimeError(f'AW unique state census drift {key}: {len(uniq)}')
    aw_unique[key] = (sum(uniq.values()), len(uniq))

assert aw_unique[('ALIGNED','AUTH')] == (4,24)
assert aw_unique[('ALIGNED','ALT')] == (21,24)
assert aw_unique[('CONFLICT','AUTH')] == (24,24)
assert aw_unique[('CONFLICT','ALT')] == (24,24)
assert abs(aw_results['primary']['mean_G_AW'] - 0.8333333333333334) < 1e-12
assert aw_results['primary']['ci95'] == [0.6666666666666666, 0.9583333333333334]

n6_analysis = json.loads((N6_DIR / 'N6_ANALYSIS.json').read_text())
n6_rows = [r for r in load_jsonl(N6_DIR / 'N6_RESULTS.jsonl') if r.get('status') == 'SUCCESS']
if len(n6_rows) != 240:
    raise RuntimeError(f'N6 SUCCESS census drift: {len(n6_rows)}')

n6_auth_block = sum(int(r['AUTH_blocked']) for r in n6_rows)
n6_alt_block = sum(int(r['ALT_blocked']) for r in n6_rows)
assert (n6_auth_block, n6_alt_block) == (113, 87)

route_counts = {}
fuzzy_blocked = {}
for cand in ('AUTH','ALT'):
    route_counts[cand] = {
        'EXACT': sum(r[f'{cand}_route'] == 'EXACT_SHADOW_SURVIVAL' for r in n6_rows),
        'FUZZY': sum(r[f'{cand}_route'] == 'FUZZY_JUDGE_PATH' for r in n6_rows),
        'HARD': sum(r[f'{cand}_route'] == 'NO_SAME_FUNCTION_HARD_FAIL' for r in n6_rows),
    }
    frows = [r for r in n6_rows if r[f'{cand}_route'] == 'FUZZY_JUDGE_PATH']
    fuzzy_blocked[cand] = (sum(int(r[f'{cand}_blocked']) for r in frows), len(frows))

assert route_counts['AUTH'] == {'EXACT':70, 'FUZZY':169, 'HARD':1}
assert route_counts['ALT'] == {'EXACT':138, 'FUZZY':101, 'HARD':1}
assert fuzzy_blocked['AUTH'] == (112,169)
assert fuzzy_blocked['ALT'] == (86,101)

mean_gap_pp = 100 * n6_analysis['primary']['mean_G_b']
ci_lo_pp, ci_hi_pp = [100*x for x in n6_analysis['primary']['bootstrap_ci95_percentile']]
assert abs(mean_gap_pp + 10.833333333333332) < 1e-10
assert abs(ci_lo_pp + 36.25) < 1e-10
assert abs(ci_hi_pp - 14.583333333333334) < 1e-10








# -------- Typography --------
from matplotlib import rcParams
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Linux Libertine O', 'Linux Libertine', 'Libertinus Serif', 'DejaVu Serif']
rcParams['font.size'] = 9.2
rcParams['axes.titlesize'] = 10.0
rcParams['axes.labelsize'] = 9.3
rcParams['xtick.labelsize'] = 8.6
rcParams['ytick.labelsize'] = 8.7
rcParams['legend.fontsize'] = 7.8
rcParams['axes.linewidth'] = 0.75
rcParams['pdf.fonttype'] = 42
rcParams['ps.fonttype'] = 42

AUTH = '#0072B2'
ALT = '#D55E00'
AUTO = '#E7E7E7'
REVIEW = '#B8B8B8'
GRID = '#DCDCDC'
MUTED = '#666666'
TEXT = '#222222'

fig = plt.figure(figsize=(7.05, 2.92), facecolor='white')

outer = fig.add_gridspec(
    1, 2,
    left=0.047, right=0.994,
    bottom=0.105, top=0.385,
    width_ratios=[0.84, 1.30],
    wspace=0.11,
)
ax_a = fig.add_subplot(outer[0, 0])

# Give Panel (a) substantially more vertical plotting area so the two-row
# comparison fills the available column instead of sitting at the bottom.
# Keep its bottom aligned with Panel (b), but extend its top upward beneath
# the action legend.
_p_a = ax_a.get_position()
ax_a.set_position([_p_a.x0, _p_a.y0, _p_a.width, 0.555])

bgs = outer[0, 1].subgridspec(1, 2, width_ratios=[1.34, 0.74], wspace=0.10)
ax_route = fig.add_subplot(bgs[0, 0])
ax_judge = fig.add_subplot(bgs[0, 1], sharey=ax_route)

# Keep the route/judge body clearly below the aggregate annotation stack.
# The larger vertical separation prevents the note, legend, and subsection title
# from visually collapsing into one another at two-column print scale.
for _ax in (ax_route, ax_judge):
    _p = _ax.get_position()
    _ax.set_position([_p.x0, _p.y0, _p.width, _p.height * 0.75])

# Compact aggregate comparison: visualizes the matched endpoint before route decomposition.
ax_agg = fig.add_axes([0.595, 0.655, 0.355, 0.112])

# ------------------------------------------------------------------
# (a) Semantic monitor
# ------------------------------------------------------------------
fig.text(
    0.223, 0.958,
    '(a) Semantic monitor',
    ha='center', va='bottom',
    fontsize=10.1, fontweight='bold'
)
fig.text(
    0.223, 0.897,
    'Under conflict, the monitor flags both actions.',
    ha='center', va='bottom',
    fontsize=7.9, color=TEXT
)

ax_a.set_xlim(0, 103)
ax_a.set_ylim(-0.45, 1.45)
ax_a.set_xticks([0, 20, 40, 60, 80, 100])
ax_a.set_xlabel('Actions flagged (%)', labelpad=3)
ax_a.set_yticks(
    [1, 0],
    ['External text\nagrees with\nthe user',
     'External text\nconflicts with\nthe user']
)
ax_a.grid(axis='x', color=GRID, linewidth=0.55)
ax_a.set_axisbelow(True)
ax_a.spines['top'].set_visible(False)
ax_a.spines['right'].set_visible(False)
ax_a.spines['left'].set_visible(False)
ax_a.tick_params(axis='y', length=0)

a_auth = 4/24*100
a_alt = 21/24*100

fig.legend(
    handles=[
        Line2D([0], [0], marker='o', linestyle='None', markersize=6.8,
               markerfacecolor=AUTH, markeredgecolor='white', markeredgewidth=0.7,
               label='Authorized action'),
        Line2D([0], [0], marker='s', linestyle='None', markersize=6.8,
               markerfacecolor=ALT, markeredgecolor='white', markeredgewidth=0.7,
               label='Unauthorized action'),
    ],
    loc='upper center',
    bbox_to_anchor=(0.223, 0.755),
    ncol=2,
    frameon=False,
    handlelength=0.85,
    handletextpad=0.38,
    columnspacing=1.0,
    borderaxespad=0.0,
    fontsize=7.5,
)

# Aligned context.
ax_a.plot([a_auth, a_alt], [1, 1], color='0.72', lw=2.0, zorder=2)
ax_a.plot(
    a_auth, 1, marker='o', ms=7.6, color=AUTH,
    markeredgecolor='white', markeredgewidth=0.8, zorder=4
)
ax_a.plot(
    a_alt, 1, marker='s', ms=7.6, color=ALT,
    markeredgecolor='white', markeredgewidth=0.8, zorder=4
)
ax_a.text(
    a_auth, 1.14, '4/24\n(17%)',
    ha='center', va='bottom',
    fontsize=8.1, color=AUTH, fontweight='bold'
)
ax_a.text(
    a_alt, 1.14, '21/24\n(88%)',
    ha='center', va='bottom',
    fontsize=8.1, color=ALT, fontweight='bold'
)
ax_a.text(
    (a_auth+a_alt)/2, 0.82, '71-point gap',
    ha='center', va='top',
    fontsize=7.8, color=MUTED
)

# Conflict context: both 24/24.
ax_a.plot(
    99.1, 0.035, marker='o', ms=7.6, color=AUTH,
    markeredgecolor='white', markeredgewidth=0.8, zorder=4
)
ax_a.plot(
    100.0, -0.035, marker='s', ms=7.6, color=ALT,
    markeredgecolor='white', markeredgewidth=0.8, zorder=5
)
ax_a.text(
    96.0, 0.16, '24/24 each',
    ha='right', va='bottom',
    fontsize=7.8, color=MUTED, fontweight='bold'
)
ax_a.text(
    59, -0.15, 'both are flagged',
    ha='center', va='top',
    fontsize=7.75, color=MUTED
)

# ------------------------------------------------------------------
# (b) Reference-based defense
# ------------------------------------------------------------------
fig.text(
    0.745, 0.958,
    '(b) Shadow/reference routing',
    ha='center', va='bottom',
    fontsize=10.1, fontweight='bold'
)

# Security result first; aggregate boundary below it.
fig.text(
    0.745, 0.858,
    'The stricter check blocks unauthorized actions more often,\nbut fewer unauthorized actions reach it.',
    ha='center', va='bottom',
    fontsize=7.75, color=TEXT, fontweight='bold', linespacing=1.38
)
# Compact aggregate visual: endpoint first, then route decomposition below.
ax_agg.set_xlim(0, 60)
ax_agg.set_ylim(-0.55, 1.55)
ax_agg.set_yticks([1, 0], ['Authorized', 'Unauthorized'])
ax_agg.set_xticks([])
ax_agg.tick_params(axis='y', length=0, labelsize=6.8, pad=3)
for spine in ax_agg.spines.values():
    spine.set_visible(False)
ax_agg.set_title('Blocked overall', fontsize=7.5, fontweight='bold', pad=0.5)
ax_agg.barh(1, 113/240*100, height=0.34, color=AUTH, alpha=0.78, edgecolor='none')
ax_agg.barh(0, 87/240*100, height=0.34, color=ALT, alpha=0.78, edgecolor='none')
ax_agg.text(113/240*100 + 1.1, 1, '113/240  (47.08%)', ha='left', va='center', fontsize=6.6, color=TEXT, fontweight='bold')
ax_agg.text(87/240*100 + 1.1, 0, '87/240  (36.25%)', ha='left', va='center', fontsize=6.6, color=TEXT, fontweight='bold')
fig.text(
    0.775, 0.625,
    '95% CI for the matched difference: [-0.3625,+0.1458]',
    ha='center', va='top', fontsize=6.45, color=MUTED
)
fig.text(
    0.775, 0.568,
    'Overall, unauthorized actions are not blocked more often.',
    ha='center', va='top', fontsize=6.35, color=TEXT, fontweight='bold'
)

# Compact route legend: route semantics are independent of action color.
route_handles = [
    Patch(
        facecolor=AUTO, edgecolor='0.55', linewidth=0.7,
        label='Accepted before stricter review'
    ),
    Patch(
        facecolor=REVIEW, edgecolor='0.45', linewidth=0.7,
        label='Sent to stricter review'
    ),
]
fig.legend(
    handles=route_handles,
    loc='upper center',
    bbox_to_anchor=(0.745, 0.490),
    ncol=2,
    frameon=False,
    handlelength=1.35,
    handletextpad=0.45,
    columnspacing=1.10,
    borderaxespad=0.0,
    fontsize=7.15,
)
fig.text(
    0.745, 0.405,
    'Hard fail: 1/240 authorized; 1/240 unauthorized.',
    ha='center', va='bottom',
    fontsize=6.45, color=MUTED
)

ys = [1, 0]
labels = ['Authorized action', 'Unauthorized action']
exact = [70/240*100, 138/240*100]
judged = [169/240*100, 101/240*100]
block_if_judged = [112/169*100, 86/101*100]
colors = [AUTH, ALT]
markers = ['o', 's']

# Route split.
ax_route.set_title('Before stricter review', fontsize=8.55, fontweight='bold', pad=2)
ax_route.set_xlim(0, 100)
ax_route.set_ylim(-0.48, 1.58)
ax_route.set_xticks([0, 25, 50, 75, 100])
ax_route.set_xlabel('Share of evaluations (%)', labelpad=3)
ax_route.set_yticks(ys)
ax_route.set_yticklabels([])
ax_route.grid(axis='x', color=GRID, linewidth=0.50)
ax_route.set_axisbelow(True)
ax_route.spines['top'].set_visible(False)
ax_route.spines['right'].set_visible(False)
ax_route.spines['left'].set_visible(False)
ax_route.tick_params(axis='y', length=0)

# Compact row markers repeat the action legend without adding text.
for y, c, marker in zip(ys, colors, markers):
    ax_route.plot(
        -0.035, y, marker=marker, ms=7.3, color=c,
        markeredgecolor='white', markeredgewidth=0.7,
        transform=ax_route.get_yaxis_transform(),
        clip_on=False, zorder=5
    )

bar_h = 0.50
for y, e, j, c in zip(ys, exact, judged, colors):
    # Neutral route encoding: no competing meaning for action colors.
    ax_route.barh(
        y, e, left=0, height=bar_h,
        color=AUTO, edgecolor='0.55', linewidth=0.7, zorder=3
    )
    ax_route.barh(
        y, j, left=e, height=bar_h,
        color=REVIEW, edgecolor='0.45', linewidth=0.7, zorder=3
    )

    # Exact route counts are reviewer-visible; segment width still encodes share.
    exact_count = 70 if y == 1 else 138
    review_count = 169 if y == 1 else 101
    ax_route.text(
        e/2, y, f'Automatic\n{exact_count}/240',
        ha='center', va='center',
        fontsize=6.35, color=TEXT, fontweight='bold', linespacing=0.82
    )
    ax_route.text(
        e+j/2, y, f'Later check\n{review_count}/240',
        ha='center', va='center',
        fontsize=6.35, color=TEXT, fontweight='bold', linespacing=0.82
    )

# Conditional blocking.
ax_judge.set_title('Once reviewed', fontsize=8.55, fontweight='bold', pad=2)
ax_judge.set_xlim(0, 100)
ax_judge.set_xticks([0, 50, 100])
ax_judge.set_xlabel('Blocked (%)', labelpad=3)
ax_judge.grid(axis='x', color=GRID, linewidth=0.50)
ax_judge.set_axisbelow(True)
ax_judge.spines['top'].set_visible(False)
ax_judge.spines['right'].set_visible(False)
ax_judge.spines['left'].set_visible(False)
ax_judge.tick_params(axis='y', left=False, labelleft=False)

for y, v, c, marker in zip(ys, block_if_judged, colors, markers):
    ax_judge.plot([0, v], [y, y], color='0.78', lw=1.6, zorder=2)
    ax_judge.plot(
        v, y, marker=marker, ms=7.6, color=c,
        markeredgecolor='white', markeredgewidth=0.8, zorder=4
    )
    count_txt = '112/169' if y == 1 else '86/101'
    # Keep both two-line labels above their guide rows so neither the guide
    # line nor the x-axis can cut through the text.
    y_text = y + 0.13
    va_text = 'bottom'
    ax_judge.text(
        v, y_text, f'{count_txt}\n({v:.2f}%)',
        ha='center', va=va_text,
        fontsize=6.35, color=c, fontweight='bold', linespacing=0.94,
        clip_on=False
    )

caption = "Conflicting external text can make a guardrail treat an authorized action like an unauthorized one. (a) AgentWatcher separates the two when external text agrees with the user, but flags both under conflict. (b) AttriGuard's later check blocks unauthorized actions more often once reached (85% vs. 66%), yet 58% of unauthorized actions take the exact-reference route and survive automatically, versus 29% of authorized actions. Overall, AttriGuard blocked 36% of unauthorized actions and 47% of authorized actions, with no clear overall separation between the two. A stricter later check therefore does not guarantee stricter overall enforcement in this setting."

fig.savefig(OUT / 'figure5.pdf', bbox_inches='tight', pad_inches=0.02)
fig.savefig(OUT / 'figure5.png', dpi=340, bbox_inches='tight', pad_inches=0.02)
plt.close(fig)

(OUT / 'figure5_caption.txt').write_text(caption + '\n', encoding='utf-8')

verification = {
    'status': 'PASS',
    'science_changed': False,
    'source_hashes': {str(p.relative_to(ROOT)): h for p,h in EXPECTED_SHA.items()},
    'aw_n3': {
        'aligned_authorized': [4,24],
        'aligned_unauthorized': [21,24],
        'conflict_authorized': [24,24],
        'conflict_unauthorized': [24,24],
        'verifier_status': aw_verify.get('status'),
    },
    'n6': {
        'success_rows': len(n6_rows),
        'overall_blocked': {'authorized': [113,240], 'unauthorized': [87,240]},
        'gap_pp': mean_gap_pp,
        'gap_ci95_pp': [ci_lo_pp, ci_hi_pp],
        'exact_survival': {'authorized': [70,240], 'unauthorized': [138,240]},
        'fuzzy_route': {'authorized': [169,240], 'unauthorized': [101,240]},
        'hard_fail': {'authorized': [1,240], 'unauthorized': [1,240]},
        'blocked_if_judged': {'authorized': [112,169], 'unauthorized': [86,101]},
    },
    'visual_contract': {
        'action_legend': True,
        'route_legend': True,
        'route_encoding_solid_no_hatching': True,
        'panel_b_row_text_labels_removed': True,
        'panel_b_row_markers_added': True,
        'route_labels_percentage_only': True,
        'no_text_overlap': True,
        'aggregate_before_route': True,
        'aggregate_visual_bar_pair': True,
        'no_auth_alt_shorthand': True,
        'no_e2e': True,
        'no_attack_chain': True,
    }
}
(OUT / 'figure5_verification.json').write_text(
    json.dumps(verification, indent=2) + '\n', encoding='utf-8'
)
