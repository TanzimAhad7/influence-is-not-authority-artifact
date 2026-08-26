from pathlib import Path
import os, csv, json, hashlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

EXPECTED_SHA256 = {
    "R2B_JTF_FREEZE.json": "29e5214c733b1bfcf2bfc7b4adb0c165d36343f310b34a0fa2630947d4f67d45",
    "R2B_JTF_RESULTS.json": "ee5becff3cdf1397a088d82f1487ce0af4eea3c202f7cc78eb3c3a6c38f5991f",
    "R2B_JTF_FRONTIER_llama.csv": "aee885ed9a001b0f368a954aeaf657c2b1fb9e288cdda633bc4d54d817149fc2",
    "R2B_JTF_FRONTIER_gemma.csv": "c8daf9a8fcbb8152a8331965ae5dbd7d87cd49f0b9f6d2fec4b212922fff13ee",
    "RUN_COMPLETE.json": "4d63c72ea0a19b69954d601f9e7c006e3ff67b163e0587b8f15a8e6e48e1c9df",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

R2B = Path(os.environ.get("PHASE0_ROOT", "/mnt/data/phase0_stage1")) / "artifacts" / "R2B_JTF_AUTHOR_v1"
for name, expected in EXPECTED_SHA256.items():
    actual = sha256(R2B / name)
    assert actual == expected, f"hash mismatch: {name}: {actual}"

results = json.loads((R2B / "R2B_JTF_RESULTS.json").read_text())
freeze = json.loads((R2B / "R2B_JTF_FREEZE.json").read_text())
run_complete = json.loads((R2B / "RUN_COMPLETE.json").read_text())
assert results["status"] == "R2B_JTF_ANALYSIS_COMPLETE"
assert freeze["census"]["n_bases"] == 24
assert run_complete["no_model_provider_calls"] is True

def read_frontier(name: str):
    rows = []
    with (R2B / f"R2B_JTF_FRONTIER_{name}.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "label": r["threshold_label"],
                "tau": float(r["tau"]),
                "benign": float(r["a14_benign_flag_rate"]),
                "aivr": float(r["a14_aivr"]),
                "auth": float(r["n3_auth_flag_rate"]),
                "alt": float(r["n3_alt_flag_rate"]),
            })
    assert len(rows) == 386
    return rows

FRONTIERS = {"Llama": read_frontier("llama"), "Gemma": read_frontier("gemma")}

def zero_harmless_point(rows):
    eligible = [r for r in rows if r["benign"] == 0.0 and r["aivr"] == 0.0 and r["auth"] == 0.0]
    best = max(r["alt"] for r in eligible)
    return [r for r in eligible if r["alt"] == best][-1]

def benign_alt_path(rows):
    ordered = sorted([r for r in rows if r["label"] != "tau0"], key=lambda r: r["tau"])
    out, last = [], None
    for r in ordered:
        state = (r["benign"], r["alt"])
        if state != last:
            out.append(r)
            last = state
    return out

# Frozen manuscript-bearing anchors.
assert np.isclose(zero_harmless_point(FRONTIERS["Llama"])["alt"], 12/48)
assert np.isclose(zero_harmless_point(FRONTIERS["Gemma"])["alt"], 18/48)

font_dir = Path("/usr/share/fonts/opentype/linux-libertine")
if font_dir.exists():
    REG = FontProperties(fname=str(font_dir / "LinLibertine_R.otf"))
    BOLD = FontProperties(fname=str(font_dir / "LinLibertine_RB.otf"))
else:
    REG = FontProperties(family="DejaVu Serif")
    BOLD = FontProperties(family="DejaVu Serif", weight="bold")

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 8.4})
LLAMA = "#0072B2"
GEMMA = "#D55E00"
GRID = "#DDDDDD"

# Single-column geometry: stack the two scorers instead of shrinking a landscape figure.
fig = plt.figure(figsize=(3.30, 2.75), facecolor="white")
gs = fig.add_gridspec(2, 1, left=0.20, right=0.985, bottom=0.18, top=0.90, hspace=0.38)
axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0])]

def draw_panel(ax, model, color, letter):
    path = benign_alt_path(FRONTIERS[model])
    x = np.array([r["benign"] for r in path]) * 100
    y = np.array([r["alt"] for r in path]) * 100
    zero = zero_harmless_point(FRONTIERS[model])

    ax.set_xlim(-3, 103)
    ax.set_ylim(-3, 103)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.grid(True, color=GRID, lw=0.45, alpha=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_linewidth(0.85)
    ax.tick_params(axis="both", width=0.8, length=3.0, pad=2)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontproperties(REG)
        lab.set_fontsize(7.5)

    ax.step(x, y, where="post", color=color, lw=1.5, zorder=3)
    # Same ideal authorization target as the original two-column figure.
    ax.plot([0], [100], marker="x", ms=5.5, mew=1.15, color="0.35", zorder=6)
    if model == "Llama":
        ax.text(
            4.5, 97.0,
            "Catch unauthorized actions\nwithout flagging authorized ones.",
            ha="left", va="top",
            fontproperties=REG, fontsize=6.65, color="0.36",
            linespacing=0.92,
        )

    zx, zy = zero["benign"] * 100, zero["alt"] * 100
    ax.scatter([zx], [zy], s=42, marker="o", color=color, edgecolors="white", linewidths=0.75, zorder=7)
    missed = 100.0 - zy
    # Preserve the original label placement logic: put the label below the
    # first horizontal frontier segment so it never sits on the step curve.
    label_y = 18.0 if model == "Llama" else 24.0
    ax.annotate(
        f"{missed:.1f}% unauthorized actions missed",
        xy=(zx, zy), xytext=(8.0, label_y), ha="left", va="center",
        fontproperties=BOLD, fontsize=7.15, color=color,
        arrowprops=dict(arrowstyle="-", color=color, lw=0.68, shrinkA=3, shrinkB=4),
    )
    ax.text(0.5, 1.06, f"({letter})  {model} scorer", transform=ax.transAxes,
            ha="center", va="bottom", fontproperties=BOLD, fontsize=8.5)


for ax, model, color, letter in [
    (axes[0], "Llama", LLAMA, "a"),
    (axes[1], "Gemma", GEMMA, "b"),
]:
    draw_panel(ax, model, color, letter)

axes[0].set_xlabel("")
axes[1].set_xlabel("Harmless authorized cases flagged (%)", fontproperties=REG, fontsize=8.2, labelpad=2)
fig.text(0.035, 0.535, "Unauthorized actions flagged (%)", rotation=90,
         ha="center", va="center", fontproperties=REG, fontsize=8.2)

out = Path(__file__).resolve().parent
fig.savefig(out / "figure4.pdf", bbox_inches="tight", pad_inches=0.02)
fig.savefig(out / "figure4_singlecol_preview.png", dpi=300, bbox_inches="tight", pad_inches=0.02)
plt.close(fig)
print(out / "figure4.pdf")
