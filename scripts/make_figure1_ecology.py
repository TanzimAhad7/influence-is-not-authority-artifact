#!/usr/bin/env python3
"""
Figure 1 generator for the USENIX Security '27 artifact.

Paper:
    Causal Dependence Is Not Authority:
    Stress-Testing Authorization in LLM Agent Guardrails

Purpose:
    Generate the ecological motivation / authorization-vs-causal-dependence
    main-paper figure directly from saved analysis artifacts.

Inputs (relative to project root):
    artifacts/BASE_FINISHING_ZERO_CALL_v1/P3_C0/P3_C0_REFRESH.json
    artifacts/b1_a12_backbone_replication_c0_v2/gpt4o/results.json
    artifacts/b1_a12_backbone_replication_c0_v2/claude45/results.json

Outputs:
    artifacts/figures/main/Figure1_ecology_authority.png
    artifacts/figures/main/Figure1_ecology_authority.pdf
    artifacts/figures/main/Figure1_ecology_authority.svg
    artifacts/figures/main/Figure1_ecology_authority_summary.txt

Scientific behavior:
    - Zero model/provider calls.
    - No result re-estimation.
    - Reads saved analysis outputs and renders them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def add_box(ax, xy, w, h, text, fontsize=11):
    box = FancyBboxPatch(
        xy, w, h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.5,
        edgecolor="black",
        facecolor="white",
    )
    ax.add_patch(box)
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text,
            ha="center", va="center", fontsize=fontsize)


def resolve_paths(root: Path):
    art = root / "artifacts"
    paths = {
        "a13_p3": art / "BASE_FINISHING_ZERO_CALL_v1" / "P3_C0" / "P3_C0_REFRESH.json",
        "b1_gpt4o": art / "b1_a12_backbone_replication_c0_v2" / "gpt4o" / "results.json",
        "b1_claude": art / "b1_a12_backbone_replication_c0_v2" / "claude45" / "results.json",
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required input files:\n" + "\n".join(missing))
    return paths


def main():
    ap = argparse.ArgumentParser(description="Generate USENIX Figure 1 from saved artifact results.")
    ap.add_argument("--root", default=".", help="Project root containing artifacts/")
    ap.add_argument("--outdir", default=None, help="Optional output directory override")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    outdir = Path(args.outdir).resolve() if args.outdir else root / "artifacts" / "figures" / "main"
    outdir.mkdir(parents=True, exist_ok=True)

    paths = resolve_paths(root)
    a13 = load_json(paths["a13_p3"])
    b1_gpt = load_json(paths["b1_gpt4o"])
    b1_claude = load_json(paths["b1_claude"])

    a13_head = a13["frozen_A13_C0_headline"]
    a13_pop = a13["population"]
    a13_suite = a13["leave_one_suite_out"]

    headline_diff = a13_head["difference"]
    headline_lo, headline_hi = a13_head["ci95"]
    headline_spec = a13_head["specified_mean"]
    headline_del = a13_head["delegated_mean"]
    headline_ns = a13_head["n_specified_tasks"]
    headline_nd = a13_head["n_delegated_tasks"]

    def b1_extract(d):
        h = d["primary_H_mean_del"]
        c = d["counts"]
        return {
            "specified_mean": h["specified_mean"],
            "delegated_mean": h["delegated_mean"],
            "difference": h["difference"],
            "ci95": h["ci95"],
            "n_specified_tasks": h["n_specified_tasks"],
            "n_delegated_tasks": h["n_delegated_tasks"],
            "valid_extreme_decisions": c["primary_valid_confirmatory_extreme_label_decisions"],
            "valid_tasks": c["primary_valid_confirmatory_tasks"],
        }

    b1g = b1_extract(b1_gpt)
    b1c = b1_extract(b1_claude)

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.35], width_ratios=[1.1, 1.0], hspace=0.35, wspace=0.25)
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])

    # Panel A: conceptual framing
    ax_a.set_axis_off()
    ax_a.set_xlim(0, 1)
    ax_a.set_ylim(0, 1)
    ax_a.text(0.0, 1.02, "A. Security distinction: causal dependence is not authority",
              fontsize=14, fontweight="bold", ha="left", va="bottom")

    add_box(ax_a, (0.05, 0.48), 0.22, 0.25,
            "Authorized action\n\nUser task is permitted\nunder the stated policy")
    add_box(ax_a, (0.39, 0.48), 0.22, 0.25,
            "External evidence / context\n\nemail, retrieved content,\nreference document")
    add_box(ax_a, (0.73, 0.48), 0.22, 0.25,
            "Observable causal support\n\nmodel/guardrail behavior\nchanges when evidence changes")

    ax_a.annotate("", xy=(0.39, 0.60), xytext=(0.27, 0.60), arrowprops=dict(arrowstyle="->", lw=1.6))
    ax_a.annotate("", xy=(0.73, 0.60), xytext=(0.61, 0.60), arrowprops=dict(arrowstyle="->", lw=1.6))
    ax_a.text(0.50, 0.27,
              "Security question: does observable causal dependence imply that the evidence itself carries\n"
              "authorization information or policy authority?\n\n"
              "Authorized evidence can be causally necessary without itself being an authorization signal.",
              ha="center", va="center", fontsize=11)

    # Panel B: A13-C0 + leave-one-suite robustness
    ax_b.set_title("B. A13-C0 ecological evidence and leave-one-suite robustness",
                   fontsize=13, fontweight="bold", loc="left")

    rows = [{"label": "A13-C0 headline", "diff": headline_diff, "lo": headline_lo,
             "hi": headline_hi, "n": a13_pop["valid_tasks"]}]
    for r in a13_suite:
        rows.append({"label": f"Leave out {r['excluded_suite']}", "diff": r["H_difference"],
                     "lo": r["H_ci_low"], "hi": r["H_ci_high"], "n": r["n_tasks_remaining"]})

    y = np.arange(len(rows))
    diffs = np.array([r["diff"] for r in rows])
    lower = diffs - np.array([r["lo"] for r in rows])
    upper = np.array([r["hi"] for r in rows]) - diffs

    ax_b.errorbar(diffs, y, xerr=[lower, upper], fmt="o", color="black", ecolor="black",
                  elinewidth=1.5, capsize=4, markersize=6)
    ax_b.axvline(0, linestyle="--", linewidth=1)
    ax_b.axvline(headline_diff, linestyle=":", linewidth=1)
    ax_b.set_yticks(y)
    ax_b.set_yticklabels([r["label"] for r in rows], fontsize=10)
    ax_b.invert_yaxis()
    ax_b.set_xlabel("Task-clustered H difference (SPECIFIED − DELEGATED)", fontsize=11)

    xmin = min(r["lo"] for r in rows) - 0.08
    xmax = max(r["hi"] for r in rows) + 0.10
    ax_b.set_xlim(xmin, xmax)
    for i, r in enumerate(rows):
        ax_b.text(xmax - 0.01, i,
                  f"{r['diff']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]   n={r['n']}",
                  va="center", ha="right", fontsize=9)

    ax_b.text(0.02, -0.22,
              f"Primary population: {a13_pop['rows']} rows → {a13_pop['valid_decisions']} primary-valid decisions / "
              f"{a13_pop['valid_tasks']} tasks.\n"
              f"Headline: SPECIFIED={headline_spec:.3f}, DELEGATED={headline_del:.3f}, "
              f"Δ={headline_diff:+.4f}, 95% CI [{headline_lo:+.4f}, {headline_hi:+.4f}].\n"
              "All leave-one-suite point estimates remain positive; banking/workspace CIs cross zero.",
              transform=ax_b.transAxes, fontsize=9, va="top")

    # Panel C: B1 breadth
    ax_c.set_title("C. Breadth across trajectory backbones", fontsize=13, fontweight="bold", loc="left")
    groups = ["A13-C0", "B1 GPT-4o", "B1 Claude 4.5"]
    spec_vals = [headline_spec, b1g["specified_mean"], b1c["specified_mean"]]
    del_vals = [headline_del, b1g["delegated_mean"], b1c["delegated_mean"]]
    diffs_c = [headline_diff, b1g["difference"], b1c["difference"]]
    cis_c = [(headline_lo, headline_hi), tuple(b1g["ci95"]), tuple(b1c["ci95"])]
    ns = [(headline_ns, headline_nd),
          (b1g["n_specified_tasks"], b1g["n_delegated_tasks"]),
          (b1c["n_specified_tasks"], b1c["n_delegated_tasks"])]

    x = np.arange(len(groups))
    w = 0.34
    ax_c.bar(x - w/2, spec_vals, width=w, edgecolor="black", linewidth=1.2, label="SPECIFIED")
    ax_c.bar(x + w/2, del_vals, width=w, edgecolor="black", linewidth=1.2, color="0.80", label="DELEGATED")
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(groups, fontsize=10)
    ax_c.set_ylabel("Task-level mean-delete success rate (H)", fontsize=11)
    ax_c.set_ylim(0, 1.02)
    ax_c.legend(frameon=False, loc="upper right")

    for i in range(len(groups)):
        lo, hi = cis_c[i]
        ax_c.text(x[i], max(spec_vals[i], del_vals[i]) + 0.06,
                  f"Δ={diffs_c[i]:+.3f}\n95% CI [{lo:+.3f}, {hi:+.3f}]",
                  ha="center", va="bottom", fontsize=9)
        ax_c.text(x[i], 0.02, f"nS={ns[i][0]}, nD={ns[i][1]}", ha="center", va="bottom", fontsize=8)

    ax_c.text(0.02, -0.22,
              "B1 provides directional breadth rather than replacing the primary A13-C0 ecological estimand.\n"
              "Both B1 replications retain a positive H direction, but their confidence intervals include zero.",
              transform=ax_c.transAxes, fontsize=9, va="top")

    fig.suptitle("Ecological motivation: causal dependence can arise within already-authorized agent behavior",
                 fontsize=15, y=0.99)

    stem = outdir / "Figure1_ecology_authority"
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)

    summary_path = outdir / "Figure1_ecology_authority_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Figure 1 numerical summary\n==========================\n\n")
        f.write(f"A13-C0: rows={a13_pop['rows']}, valid_decisions={a13_pop['valid_decisions']}, "
                f"valid_tasks={a13_pop['valid_tasks']}\n")
        f.write(f"SPECIFIED={headline_spec:.6f}, DELEGATED={headline_del:.6f}, "
                f"difference={headline_diff:.6f}, CI=[{headline_lo:.6f}, {headline_hi:.6f}]\n\n")
        f.write("Leave-one-suite-out:\n")
        for r in a13_suite:
            f.write(f"  {r['excluded_suite']}: {r['H_difference']:.6f} "
                    f"[{r['H_ci_low']:.6f}, {r['H_ci_high']:.6f}], n_tasks={r['n_tasks_remaining']}\n")
        f.write("\nB1 GPT-4o:\n")
        f.write(f"  difference={b1g['difference']:.6f}, CI=[{b1g['ci95'][0]:.6f}, {b1g['ci95'][1]:.6f}], "
                f"extreme_decisions={b1g['valid_extreme_decisions']}, tasks={b1g['valid_tasks']}\n")
        f.write("\nB1 Claude 4.5:\n")
        f.write(f"  difference={b1c['difference']:.6f}, CI=[{b1c['ci95'][0]:.6f}, {b1c['ci95'][1]:.6f}], "
                f"extreme_decisions={b1c['valid_extreme_decisions']}, tasks={b1c['valid_tasks']}\n")

    print(f"[done] {stem.with_suffix('.png')}")
    print(f"[done] {stem.with_suffix('.pdf')}")
    print(f"[done] {stem.with_suffix('.svg')}")
    print(f"[done] {summary_path}")


if __name__ == "__main__":
    main()