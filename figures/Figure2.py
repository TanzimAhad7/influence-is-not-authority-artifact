from pathlib import Path
import os
import json, hashlib
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

# ------------------------------------------------------------
# Data loading and verification from frozen A14 artifacts
# ------------------------------------------------------------
def _locate_phase0_root():
    env = os.environ.get("PHASE0_ROOT")
    candidates = []
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.extend([here.parent, *here.parents[:4], Path.cwd()])
    for base in candidates:
        if (base / "artifacts" / "a14_minimal_factorial").exists():
            return base
    raise FileNotFoundError("Could not locate phase0_pilot root; set PHASE0_ROOT.")

PHASE0_ROOT = _locate_phase0_root()
ROOT = PHASE0_ROOT / "artifacts" / "a14_minimal_factorial"
RESULTS = ROOT / 'analysis/results.json'
LLAMA = ROOT / 'scorer_llama/condition_scores.jsonl'
GEMMA = ROOT / 'scorer_gemma/condition_scores.jsonl'
AUDIT = ROOT / 'human_base_quartet_audit.jsonl'
EXPECTED = {
    RESULTS: 'ef0eb44df3b2388c2b665f2a86b8602ca5a1cb7a3601eac933becb71b95e099c',
    LLAMA: '1c2ee74880a4a74d2bbfad06a6fad4e0f8c09a0fd474d8a0a9a7e43f5fb91111',
    GEMMA: 'edbf606d112410e50ff260e63d7008470c5299ddabfd43188ed7d942c42ec0fa',
    AUDIT: 'c1f3ae4cac257acf2df3f7b9bea8419a30bfe818c9c4e7be41574adae6ee7955',
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


for p, h in EXPECTED.items():
    if sha256(p) != h:
        raise RuntimeError(f'hash mismatch for {p}')

audit = read_jsonl(AUDIT)
assert len(audit) == 24
assert all(r['human_all_four_authorization_equivalent'] for r in audit)
assert all(r['same_exact_target_action_all_four'] for r in audit)
assert all(r['same_authorization_policy_hash_all_four'] for r in audit)
assert all(r['outcome_blinded'] for r in audit)

D = json.loads(RESULTS.read_text())


def paired_margins(rows):
    by = defaultdict(dict)
    for r in rows:
        by[r['base_id']][(r['factor_provenance'], r['factor_descendant'])] = r
    out = []
    for bid, c in sorted(by.items()):
        user = 0.5 * (c[('USER_ID', 'SHAM')]['CA_MARGIN'] + c[('USER_ID', 'ECHO')]['CA_MARGIN'])
        tool = 0.5 * (c[('TOOL_ID', 'SHAM')]['CA_MARGIN'] + c[('TOOL_ID', 'ECHO')]['CA_MARGIN'])
        out.append((bid, user, tool, tool - user))
    return out


def support_shifts(rows):
    by = defaultdict(dict)
    for r in rows:
        by[r['base_id']][(r['factor_provenance'], r['factor_descendant'])] = r

    def exec_group_margin(r, group):
        fac = r['action_token_factorization']
        n = r['completion_token_count']
        return (fac['DELETE__U'].get(group, 0.0) - fac['DELETE__S_REL'].get(group, 0.0)) / n

    du, ds, ex, whole = [], [], [], []
    for _, c in sorted(by.items()):
        def p1(fn):
            us = fn(c[('USER_ID', 'SHAM')])
            ue = fn(c[('USER_ID', 'ECHO')])
            ts = fn(c[('TOOL_ID', 'SHAM')])
            te = fn(c[('TOOL_ID', 'ECHO')])
            return 0.5 * ((ts - us) + (te - ue))

        du.append(p1(lambda r: r['bar_dU_fixed']))
        ds.append(p1(lambda r: r['bar_dS_relevant']))
        ex.append(p1(lambda r: exec_group_margin(r, 'EXECUTION_IDENTIFIER')))
        whole.append(p1(lambda r: r['CA_MARGIN']))

    du = np.asarray(du)
    ds = np.asarray(ds)
    ex = np.asarray(ex)
    whole = np.asarray(whole)
    return float(du.mean()), float(ds.mean()), float(abs(ex.mean()) / abs(whole.mean()) * 100.0)


ll_rows = read_jsonl(LLAMA)
gm_rows = read_jsonl(GEMMA)
LL = paired_margins(ll_rows)
GM = paired_margins(gm_rows)
MECH = {'Llama': support_shifts(ll_rows), 'Gemma': support_shifts(gm_rows)}

# ------------------------------------------------------------
# Figure styling
# ------------------------------------------------------------
libertine = '/usr/share/fonts/opentype/linux-libertine'
if Path(libertine).exists():
    REG = FontProperties(fname=f'{libertine}/LinLibertine_R.otf')
    BOLD = FontProperties(fname=f'{libertine}/LinLibertine_RB.otf')
    ITAL = FontProperties(fname=f'{libertine}/LinLibertine_RI.otf')
else:
    REG = FontProperties(family='DejaVu Serif')
    BOLD = FontProperties(family='DejaVu Serif', weight='bold')
    ITAL = FontProperties(family='DejaVu Serif', style='italic')

plt.rcParams.update({'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none', 'font.size': 8.9})
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
LC, GC = colors[0], colors[1]

fig = plt.figure(figsize=(10.2, 5.72), facecolor='white')
outer = GridSpec(
    1, 2, figure=fig, width_ratios=[1.06, 0.94],
    left=0.058, right=0.985, top=0.965, bottom=0.082, wspace=0.050
)

# subtle panel divider
fig.lines.append(Line2D([0.532, 0.532], [0.082, 0.865], transform=fig.transFigure,
                        color='0.60', lw=0.8, ls=':'))

# ------------------------------------------------------------
# Left panel (a): matched score movement
# ------------------------------------------------------------
left = GridSpecFromSubplotSpec(
    4, 1, subplot_spec=outer[0, 0],
    height_ratios=[0.46, 0.64, 1.44, 1.44], hspace=0.17
)
ax_tl = fig.add_subplot(left[0, 0]); ax_tl.axis('off')
ax_sc = fig.add_subplot(left[1, 0]); ax_sc.axis('off')
L1 = GridSpecFromSubplotSpec(1, 2, subplot_spec=left[2, 0], width_ratios=[0.76, 0.24], wspace=0.045)
L2 = GridSpecFromSubplotSpec(1, 2, subplot_spec=left[3, 0], width_ratios=[0.76, 0.24], wspace=0.045)
ax_l1 = fig.add_subplot(L1[0, 0]); st_l1 = fig.add_subplot(L1[0, 1]); st_l1.axis('off')
ax_l2 = fig.add_subplot(L2[0, 0], sharex=ax_l1, sharey=ax_l1); st_l2 = fig.add_subplot(L2[0, 1]); st_l2.axis('off')

ax_tl.text(0.00, 0.78,
           '(a)  Changing only the source of the required value\n      shifts every matched case',
           ha='left', va='center', fontproperties=BOLD, fontsize=14.15, linespacing=1.08)
ax_tl.text(0.00, 0.10, 'Lower scores are more attack-like.',
           ha='left', va='center', fontproperties=REG, fontsize=12.8)

# compact source-relocation schematic
# Plain text only: no boxes or fill behind USER / TOOL.
ax_sc.text(0.14, 0.60, 'USER\nprovides\nrequired value', ha='center', va='center',
           fontproperties=REG, fontsize=9.9, transform=ax_sc.transAxes)
ax_sc.text(0.88, 0.60, 'TOOL (legitimate)\nprovides the\nsame value', ha='center', va='center',
           fontproperties=REG, fontsize=9.45, transform=ax_sc.transAxes, color='black')
ax_sc.text(0.50, 0.64, 'SAME authorized action\nSAME intended effect', ha='center', va='center',
           fontproperties=BOLD, fontsize=10.7, transform=ax_sc.transAxes)
ax_sc.text(0.50, 0.14, 'Only the source changes:  user instruction → tool result',
           ha='center', va='center', fontproperties=REG, fontsize=9.55, transform=ax_sc.transAxes)
for x0, x1 in [(0.235, 0.295), (0.705, 0.795)]:
    ax_sc.add_patch(FancyArrowPatch((x0, 0.60), (x1, 0.60), arrowstyle='-|>',
                                    mutation_scale=10, lw=1.0, color='black',
                                    transform=ax_sc.transAxes))

YLO, YHI = -3.0, 2.0

def paired_plot(ax, st, arr, model, color, block, show_x=False, show_legend=False):
    ax.set_xlim(-0.18, 1.18)
    ax.set_ylim(YLO, YHI)
    ax.set_yticks([-3, -2, -1, 0, 1, 2])
    ax.set_yticklabels(['-3', '-2', '-1', '0', '1', '2'], fontproperties=REG, fontsize=10.6)
    ax.grid(axis='y', lw=0.55, alpha=0.18)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_linewidth(1.0)
    ax.tick_params(axis='both', width=1.0, length=4.5)
    ax.set_xticks([0, 1])
    if show_x:
        ax.set_xticklabels(['Value from\nuser instruction', 'Same value from\ntool result'],
                           fontproperties=REG, fontsize=11.0)
        ax.tick_params(axis='x', pad=6)
    else:
        ax.set_xticklabels([])
        ax.tick_params(axis='x', labelbottom=False)

    for _, u, t, _ in arr:
        ax.plot([0, 1], [u, t], color='0.60', lw=1.0, alpha=0.45, zorder=1)
    um = np.mean([r[1] for r in arr]); tm = np.mean([r[2] for r in arr])
    ax.plot([0, 1], [um, tm], color=color, lw=3.0, marker='o', ms=8.0, zorder=3)

    model_label_y = 0.965 if model == 'Gemma' else 1.015
    ax.text(0.035, model_label_y, model, transform=ax.transAxes, ha='left', va='bottom',
            fontproperties=BOLD, fontsize=15.1, color=color)
    if show_legend:
        legend_lines = [Line2D([0], [0], color='0.60', lw=1.5),
                        Line2D([0], [0], color=LC, lw=3.0)]
        ax.legend(legend_lines, ['one matched case ($n=24$)', 'mean change'],
                  loc='upper center', bbox_to_anchor=(0.57, 1.07), frameon=False,
                  ncol=2, columnspacing=1.0, handlelength=1.8,
                  prop=REG, fontsize=9.1, borderaxespad=0)

    mean = block['P1_PROVENANCE_MAIN']['mean']; ci = block['P1_PROVENANCE_MAIN']['ci95']
    st.text(0.02, 0.76, '24 / 24 cases', ha='left', va='center',
            fontproperties=BOLD, fontsize=11.8, color=color)
    st.text(0.02, 0.50, 'moved toward a\nmore attack-like\nscore', ha='left', va='center',
            fontproperties=REG, fontsize=9.75, linespacing=1.15)
    st.text(0.02, 0.18, f'Mean change {mean:+.2f}\n95% CI [{ci[0]:+.2f}, {ci[1]:+.2f}]',
            ha='left', va='center', fontproperties=REG, fontsize=9.35)

paired_plot(ax_l1, st_l1, LL, 'Llama', LC, D['primary_factorial_CA_MARGIN'],
            show_x=False, show_legend=True)
paired_plot(ax_l2, st_l2, GM, 'Gemma', GC, D['gemma_source_fidelity']['factorial_CA_MARGIN'],
            show_x=True, show_legend=False)

fig.text(0.014, 0.48, 'Causal-support score\n(lower = more attack-like)', rotation=90,
         ha='center', va='center', fontproperties=REG, fontsize=12.6)

# ------------------------------------------------------------
# Right panel (b): combine both scorer support shifts on one axis
# ------------------------------------------------------------
right = GridSpecFromSubplotSpec(
    3, 1, subplot_spec=outer[0, 1],
    height_ratios=[0.80, 2.43, 0.68], hspace=0.16
)
ax_tr = fig.add_subplot(right[0, 0]); ax_tr.axis('off')
ax_r = fig.add_subplot(right[1, 0])
ax_rb = fig.add_subplot(right[2, 0]); ax_rb.axis('off')

ax_tr.text(0.035, 0.79,
           '(b)  The score follows where the\n      required value comes from',
           ha='left', va='center', fontproperties=BOLD, fontsize=14.15, linespacing=1.08)
ax_tr.text(0.035, 0.19,
           'Moving the required value to the legitimate tool\n'
           'decreases user-side support and increases support\n'
           'for the relevant tool.',
           ha='left', va='center', fontproperties=REG, fontsize=11.95, linespacing=1.05)

ax_r.set_xlim(-1.05, 1.05)
ax_r.set_ylim(-0.65, 1.70)
ax_r.axvline(0, lw=1.0, color='black')
ax_r.spines[['top', 'right', 'left']].set_visible(False)
ax_r.spines['bottom'].set_linewidth(1.0)
ax_r.set_yticks([])
ax_r.set_xticks([-1.0, -0.5, 0, 0.5, 1.0])
ax_r.set_xticklabels(['−1.0', '−0.5', '0', '+0.5', '+1.0'], fontproperties=REG, fontsize=10.6)
ax_r.tick_params(axis='x', width=1.0, length=4.5, pad=5)
ax_r.set_xlabel('Mean change in attributed support', fontproperties=REG, fontsize=11.6, labelpad=4)

# column labels appear once, not once per model
ax_r.text(-0.53, 1.48, 'User-side support\n(decreases)', ha='center', va='center',
          fontproperties=REG, fontsize=11.6)
ax_r.text(+0.55, 1.48, 'Relevant-tool support\n(increases)', ha='center', va='center',
          fontproperties=REG, fontsize=11.6)

for y, model, color, vals in [(0.92, 'Llama', LC, MECH['Llama']), (0.18, 'Gemma', GC, MECH['Gemma'])]:
    du, ds, _ = vals
    ax_r.barh([y], [du], left=0, height=0.28, facecolor='white', edgecolor=color,
              linewidth=2.1, hatch='///')
    ax_r.barh([y], [ds], left=0, height=0.28, color=color, alpha=0.22,
              edgecolor=color, linewidth=1.5)
    ax_r.text(-1.02, y + 0.21, model, ha='left', va='bottom', fontproperties=BOLD,
              fontsize=14.2, color=color)
    ax_r.text(du - 0.055, y, f'{du:+.3f}'.replace('-', '−'), ha='right', va='center',
              fontproperties=BOLD, fontsize=12.0, color=color)
    ax_r.text(ds + 0.055, y, f'{ds:+.3f}', ha='left', va='center',
              fontproperties=BOLD, fontsize=12.0, color=color)

ax_rb.text(0.00, 0.42, 'Specificity check.', ha='left', va='center',
           fontproperties=BOLD, fontsize=12.0, transform=ax_rb.transAxes)
ax_rb.text(0.00, 0.04,
           f'The moved execution value accounts for {MECH["Llama"][2]:.1f}% of the total shift\n'
           f'for Llama and {MECH["Gemma"][2]:.1f}% for Gemma.',
           ha='left', va='center', fontproperties=REG, fontsize=10.95,
           transform=ax_rb.transAxes)

# ------------------------------------------------------------
# Save outputs
# ------------------------------------------------------------
out_base = Path(__file__).resolve().parent / 'figure2_gemma_lower'
fig.savefig(out_base.with_suffix('.pdf'))
fig.savefig(out_base.with_suffix('.png'), dpi=300)
fig.savefig(out_base.with_suffix('.svg'))
plt.close(fig)

caption = '''Figure 2: Authorization-fixed source relocation makes the same authorized action look more attack-like. The 24 matched base cases are the inferential units; the 96 conditions are factorial descendants of those bases. For each base, we hold authorization, the required value, the exact committed action, and the intended effect fixed, and change only where one required execution value comes from: the user instruction or a legitimate tool result. Panel (a) shows that this benign source change shifts every matched case toward the more attack-like region under both scorers (24/24 for Llama; 24/24 for Gemma). Panel (b) shows why: when the required value is attributed to the tool rather than the user, user-side support decreases while relevant-tool support increases. The specificity check shows that nearly all of the measured shift localizes to the moved execution value itself (99.7% for Llama; 96.4% for Gemma). The take-away is that the causal signal is tracking where execution-critical evidence resides, not whether the action is still authorized.'''

caption_path = Path(__file__).resolve().parent / 'figure2_USENIX_COMPACT_FINAL_v2_caption.txt'
caption_path.write_text(caption)

print(out_base.with_suffix('.pdf'))
print(out_base.with_suffix('.png'))
print(out_base.with_suffix('.svg'))
print(caption_path)
