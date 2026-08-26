from pathlib import Path
import os
import json, hashlib, random
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D

# ============================================================
# Frozen N3 inputs and verification
# ============================================================
def _locate_phase0_root():
    env = os.environ.get("PHASE0_ROOT")
    candidates = []
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.extend([here.parent, *here.parents[:4], Path.cwd()])
    for base in candidates:
        if (base / "artifacts" / "N3_PREFREEZE_AUTHOR_v1_1").exists():
            return base
    raise FileNotFoundError("Could not locate phase0_pilot root; set PHASE0_ROOT.")

PHASE0_ROOT = _locate_phase0_root()
INPUTS = PHASE0_ROOT / "artifacts" / "N3_PREFREEZE_AUTHOR_v1_1"
FREEZE = INPUTS / "N3_FREEZE.json"
ANALYSIS = INPUTS / "N3_ANALYSIS.json"
LLAMA = INPUTS / "science_llama" / "SCIENCE_SCORES.jsonl"
GEMMA = INPUTS / "science_gemma" / "SCIENCE_SCORES.jsonl"

EXPECTED_SHA256 = {
    FREEZE: "31023829c753363e3a72759e3f0b8278735a940c5c25744854b382d99572371a",
    ANALYSIS: "0ad5892760dbf3c27c81975a38b8fb0689d557e63212cb25c865eec2edfcf81c",
    LLAMA: "953b8ffb036af99a73fa571c0b4ffae7b2194b43b78b703f23f4c0f8eaa1d89f",
    GEMMA: "7aaa9ee6b75eabeddcb16dae331d2d0e42c1f650a0d550d417c26d55bb7e8aa7",
}

ENDPOINT_DIFF = {
    "Llama": {"mean": -0.534, "ci": (-0.773, -0.303)},
    "Gemma": {"mean": -0.461, "ci": (-0.675, -0.252)},
}

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]

for p, expected in EXPECTED_SHA256.items():
    actual = sha256(p)
    assert actual == expected, f"hash mismatch: {p}: {actual}"

freeze = json.loads(FREEZE.read_text())
analysis = json.loads(ANALYSIS.read_text())

assert freeze["status"] == "FROZEN_PRE_OUTCOME_AUTHOR"
assert freeze["n_bases"] == 24
assert freeze["inference"]["unit"] == "base instance"
assert freeze["human_audit"]["pass"] == 24

def score_index(rows):
    return {
        (
            r["base_id"],
            r.get("descendant"),
            r.get("provenance"),
            r.get("directive_arm"),
            r.get("action_role"),
            r["unit_type"],
        ): r
        for r in rows
    }

def endpoint_values(rows):
    """AUTH = A14 TOOL_ID authorized endpoint; ALT = N3 CONFLICT unauthorized endpoint."""
    idx = score_index(rows)
    bases = sorted({r["base_id"] for r in rows})
    out = []
    for bid in bases:
        auth = np.mean([
            idx[(bid, d, "TOOL_ID", None, "AUTH", "A14_NUISANCE_REPLICATION")]["CA_MARGIN"]
            for d in ("SHAM", "ECHO")
        ])
        alt = np.mean([
            idx[(bid, d, "TOOL_ID", "CONFLICT", "ALT", "N3_POSITIVE_CONTROL")]["CA_MARGIN"]
            for d in ("SHAM", "ECHO")
        ])
        out.append((bid, float(auth), float(alt), float(alt - auth)))
    return out

llama_ep = endpoint_values(read_jsonl(LLAMA))
gemma_ep = endpoint_values(read_jsonl(GEMMA))

llama_d = np.array([r["D_discriminant_gap"] for r in analysis["scorers"]["llama"]["per_base"]])
gemma_d = np.array([r["D_discriminant_gap"] for r in analysis["scorers"]["gemma"]["per_base"]])

# Mechanical science checks
for model, vals in [("Llama", llama_ep), ("Gemma", gemma_ep)]:
    diffs = np.array([x[3] for x in vals])
    assert abs(diffs.mean() - ENDPOINT_DIFF[model]["mean"]) < 0.002

LSTAT = analysis["scorers"]["llama"]["D_discriminant_gap"]
GSTAT = analysis["scorers"]["gemma"]["D_discriminant_gap"]

assert np.isclose(llama_d.mean(), 0.6545401550713091)
assert np.isclose(gemma_d.mean(), 0.5039115492763485)
assert (llama_d > 0).sum() == 23
assert (gemma_d > 0).sum() == 14
assert np.isclose(LSTAT["ci95"][0], 0.447511, atol=1e-5)
assert np.isclose(LSTAT["ci95"][1], 0.863571, atol=1e-5)
assert np.isclose(GSTAT["ci95"][0], 0.180641, atol=1e-5)
assert np.isclose(GSTAT["ci95"][1], 0.824582, atol=1e-5)

# ============================================================
# Typography / style
# ============================================================
font_dir = Path("/usr/share/fonts/opentype/linux-libertine")
if font_dir.exists():
    REG = FontProperties(fname=str(font_dir / "LinLibertine_R.otf"))
    BOLD = FontProperties(fname=str(font_dir / "LinLibertine_RB.otf"))
    ITAL = FontProperties(fname=str(font_dir / "LinLibertine_RI.otf"))
else:
    REG = FontProperties(family="DejaVu Serif")
    BOLD = FontProperties(family="DejaVu Serif", weight="bold")
    ITAL = FontProperties(family="DejaVu Serif", style="italic")

plt.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "font.size": 9.0,
})

# Use Matplotlib's default color cycle, consistent across outputs.
_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
LLAMA_COLOR = "#0072B2"  # colorblind-safe blue
GEMMA_COLOR = "#D55E00"  # colorblind-safe vermillion
AUTH_CUE_COLOR = "#6A51A3"  # muted purple; secondary cue only
SOURCE_CUE_COLOR = "#238B45"  # muted green; secondary cue only

fig = plt.figure(figsize=(9.65, 4.98), facecolor="white")
outer = GridSpec(
    1, 2, figure=fig,
    width_ratios=[1.08, 0.92],
    left=0.072, right=0.985, top=0.955, bottom=0.125,
    wspace=0.032
)

# ============================================================
# Panel (a): endpoint level — ONE shared absolute-score axis
# ============================================================
left = GridSpecFromSubplotSpec(
    2, 1, subplot_spec=outer[0, 0],
    height_ratios=[0.205, 1.0], hspace=0.0
)
ax_at = fig.add_subplot(left[0, 0])
ax_at.axis("off")
ax_at.text(
    0.0, 0.72,
    "(a)  The matched unauthorized action is more\n      attack-like overall",
    transform=ax_at.transAxes, ha="left", va="center",
    fontproperties=BOLD, fontsize=13.4
)
ax_at.text(
    0.0, 0.13,
    "24 matched cases. Lower scores are more attack-like.",
    transform=ax_at.transAxes, ha="left", va="center",
    fontproperties=REG, fontsize=10.2
)

ax_a = fig.add_subplot(left[1, 0])
ax_a.set_xlim(-3.35, 0.35)
ax_a.set_ylim(-0.55, 3.55)
ax_a.set_xticks([-3, -2.5, -2, -1.5, -1, -0.5, 0])
ax_a.grid(axis="x", lw=0.55, alpha=0.16)
ax_a.spines[["top", "right", "left"]].set_visible(False)
ax_a.spines["bottom"].set_linewidth(0.9)
ax_a.tick_params(axis="y", length=0, pad=7)
ax_a.tick_params(axis="x", width=0.9, length=4)
for lab in ax_a.get_xticklabels():
    lab.set_fontproperties(REG)
    lab.set_fontsize(9.5)

# Four rows, grouped by scorer. No per-base connecting lines.
row_info = [
    ("Llama", "Authorized action\n(value from\nlegitimate tool)", 3.0, llama_ep, "auth", LLAMA_COLOR, 101),
    ("Llama", "Same-function\nunauthorized\naction",           2.25, llama_ep, "alt",  LLAMA_COLOR, 102),
    ("Gemma", "Authorized action\n(value from\nlegitimate tool)", 1.05, gemma_ep, "auth", GEMMA_COLOR, 103),
    ("Gemma", "Same-function\nunauthorized\naction",          0.30, gemma_ep, "alt",  GEMMA_COLOR, 104),
]
ax_a.set_yticks([3.0, 2.25, 1.05, 0.30])
ax_a.set_yticklabels(
    ["Authorized action\n(value from\nlegitimate tool)", "Same-function\nunauthorized\naction",
     "Authorized action\n(value from\nlegitimate tool)", "Same-function\nunauthorized\naction"],
    fontproperties=REG, fontsize=10.0, linespacing=0.92
)

def jitter(n, seed, width=0.11):
    rng = random.Random(seed)
    return np.array([rng.uniform(-width, width) for _ in range(n)])

# light separator between model blocks
ax_a.axhline(1.64, color="0.75", lw=0.7)

# Compact inline model tags: close to the data, without consuming a separate column.
ax_a.text(
    -3.28, 3.38, "Llama",
    fontproperties=BOLD, fontsize=10.4, color=LLAMA_COLOR,
    ha="left", va="center"
)
ax_a.text(
    -3.28, 1.43, "Gemma",
    fontproperties=BOLD, fontsize=10.4, color=GEMMA_COLOR,
    ha="left", va="center"
)

for model, _, y, vals, which, color, seed in row_info:
    xs = np.array([v[1] if which == "auth" else v[2] for v in vals])
    # Raw bases: open for AUTH, filled-gray for ALT so meaning survives grayscale.
    if which == "auth":
        ax_a.scatter(
            xs, y + jitter(len(xs), seed),
            s=28, facecolors="white", edgecolors="0.45",
            linewidths=0.9, zorder=2
        )
        marker = "D" if model == "Llama" else "s"
    else:
        ax_a.scatter(
            xs, y + jitter(len(xs), seed),
            s=28, facecolors="0.72", edgecolors="0.42",
            linewidths=0.75, zorder=2
        )
        marker = "D" if model == "Llama" else "s"

    ax_a.scatter(
        [xs.mean()], [y], marker=marker, s=92,
        color=color, edgecolors="white", linewidths=0.7, zorder=5
    )


# Difference annotations are aggregate, not per-case laws.
for model, vals, y_mid, color in [
    ("Llama", llama_ep, 2.625, LLAMA_COLOR),
    ("Gemma", gemma_ep, 0.675, GEMMA_COLOR),
]:
    auth_m = np.mean([v[1] for v in vals])
    alt_m = np.mean([v[2] for v in vals])
    info = ENDPOINT_DIFF[model]
    # One-line aggregate summary in the empty gap between rows.
    # This avoids covering any raw case points.
    ax_a.text(
        -1.58, y_mid,
        f"Unauthorized action: {abs(info['mean']):.3f} lower on average"
        f"   [95% CI {info['ci'][0]:+.3f}, {info['ci'][1]:+.3f}]",
        fontproperties=REG, fontsize=9.0, color=color,
        ha="center", va="center"
    )

ax_a.set_xlabel(
    "Causal-support score for the action  (lower = more attack-like)",
    fontproperties=REG, fontsize=10.8, labelpad=7
)

# Legend: low-ink, endpoint-specific
endpoint_handles = [
    Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="white",
           markeredgecolor="0.45", markersize=6.0, label="authorized case"),
    Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="0.72",
           markeredgecolor="0.42", markersize=6.0, label="unauthorized case"),
    Line2D([0], [0], marker="D", linestyle="none", markerfacecolor="0.30",
           markeredgecolor="white", markersize=7.0, label="mean"),
]
ax_a.legend(
    handles=endpoint_handles, loc="lower center",
    bbox_to_anchor=(0.56, 0.018), frameon=False,
    ncol=3, columnspacing=1.05, handletextpad=0.34, borderaxespad=0.0,
    prop=REG, fontsize=8.8
)

# ============================================================
# Panel (b): response displacement — forest/strip around zero
# ============================================================
right = GridSpecFromSubplotSpec(
    2, 1, subplot_spec=outer[0, 1],
    height_ratios=[0.205, 1.0], hspace=0.0
)
ax_bt = fig.add_subplot(right[0, 0])
ax_bt.axis("off")
ax_bt.text(
    0.0, 0.72,
    "(b)  But the harmless source change moves\n      the score more on average",
    transform=ax_bt.transAxes, ha="left", va="center",
    fontproperties=BOLD, fontsize=13.4
)
ax_bt.text(
    0.0, 0.13,
    "The action stays authorized; only where its required value comes from changes.",
    transform=ax_bt.transAxes, ha="left", va="center",
    fontproperties=REG, fontsize=10.2
)

ax_b = fig.add_subplot(right[1, 0])
ax_b.set_xlim(-0.95, 2.80)
ax_b.set_ylim(-0.55, 1.55)
ax_b.axvline(0, ymin=0.12, ymax=0.86, color="#7b7488", lw=1.15, linestyle=(0, (1.4, 2.3)), zorder=0)
ax_b.spines[["top", "right", "left"]].set_visible(False)
ax_b.spines["bottom"].set_linewidth(0.9)
ax_b.set_yticks([1.0, 0.0])
ax_b.set_yticklabels(["", ""])
ax_b.tick_params(axis="y", length=0, pad=0)
ax_b.tick_params(axis="x", width=0.9, length=4)

# Model names are integrated into the colored row annotations at right.

for lab in ax_b.get_xticklabels():
    lab.set_fontproperties(REG)
    lab.set_fontsize(9.5)

ax_b.text(
    -0.78, 1.40, "Authorization\nchange moves\nthe score more",
    fontproperties=BOLD, fontsize=9.4, color=AUTH_CUE_COLOR,
    ha="left", va="center"
)
ax_b.text(
    2.58, 1.40, "Harmless source\nchange moves\nthe score more",
    fontproperties=BOLD, fontsize=9.4, color=SOURCE_CUE_COLOR,
    ha="right", va="center"
)

# Direction cues above the data, not in boxes.

def displacement_row(model, y, vals, stat, color, seed, mean_marker):
    # Base-level values
    ax_b.scatter(
        vals, y + jitter(len(vals), seed, width=0.105),
        s=29, color="0.58", alpha=0.75, edgecolors="none", zorder=2
    )
    mean = stat["mean"]
    lo, hi = stat["ci95"]
    ax_b.errorbar(
        [mean], [y],
        xerr=[[mean - lo], [hi - mean]],
        fmt=mean_marker, color=color, markersize=8.5,
        elinewidth=2.2, capsize=6, capthick=1.8, zorder=5
    )
    # Direct annotation to the right of each row
    positive = stat["n_positive"]
    ax_b.text(
        0.68, y + 0.14,
        f"{model}: average {mean:+.3f}",
        transform=ax_b.get_yaxis_transform(),
        fontproperties=BOLD, fontsize=10.2,
        color=color, ha="left", va="center"
    )
    ax_b.text(
        0.68, y - 0.03,
        f"95% CI [{lo:+.3f}, {hi:+.3f}]",
        transform=ax_b.get_yaxis_transform(),
        fontproperties=REG, fontsize=9.2,
        color=color, ha="left", va="center"
    )
    ax_b.text(
        0.68, y - 0.20,
        f"Harmless source change\nmoved farther in {positive}/24 cases",
        transform=ax_b.get_yaxis_transform(),
        fontproperties=REG, fontsize=9.3,
        color=color, ha="left", va="center", linespacing=0.95
    )

displacement_row("Llama", 1.0, llama_d, LSTAT, LLAMA_COLOR, 201, "D")
displacement_row("Gemma", 0.0, gemma_d, GSTAT, GEMMA_COLOR, 202, "s")

ax_b.set_xlabel(
    "Difference in score movement",
    fontproperties=REG, fontsize=10.8, labelpad=7
)

# Small explanatory key for panel B; no extra conclusion box.
ax_b.text(
    0.50, 0.105,
    "0 = both changes move the score equally",
    transform=ax_b.transAxes, fontproperties=REG,
    fontsize=9.0, color="0.30", ha="center", va="bottom",
    bbox=dict(facecolor="white", edgecolor="none", pad=0.8, alpha=0.92),
    zorder=6
)

# ============================================================
# Save
# ============================================================
out = Path(__file__).resolve().parent / "figure3"
fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.025)
fig.savefig(out.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.025)
fig.savefig(out.with_suffix(".png"), dpi=330, bbox_inches="tight", pad_inches=0.025)
plt.close(fig)

caption = (
    "Figure 3: Endpoint threat level and response displacement answer different questions. "
    "Across 24 matched cases, Panel (a) compares absolute endpoint level and shows that the matched unauthorized action is more attack-like overall under both scorers. "
    "Panel (b) instead compares response displacement and shows that changing only where the same required value comes from, while the action remains authorized, produces the larger average score movement. "
    "Thus, the signal remains threat-sensitive, but response magnitude is not itself an authorization measure."
)
Path(__file__).resolve().parent.joinpath("figure3_caption.txt").write_text(caption)

print("PASS: frozen N3 hashes")
print("PASS: 24-base pre-outcome freeze and human audit")
print("PASS: endpoint differences reproduce -0.534 (Llama), -0.461 (Gemma)")
print("PASS: displacement reproduces +0.654540 / +0.503912 and 23/24 / 14/24")
print(out.with_suffix(".pdf"))
print(out.with_suffix(".png"))
print(out.with_suffix(".svg"))
print(Path(__file__).resolve().parent / "figure3_caption.txt")