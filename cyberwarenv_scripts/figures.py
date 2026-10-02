"""Generate publication-style figures (English labels per IEEE TDSC
figure conventions; the target journals are English-language venues).

Figure 1: Training curves (eval CSR vs steps) — all cells, with paper
          claim lines where applicable.
Figure 2: Final CSR comparison with 95% CIs vs legacy claims.
Figure 3: Calibration sweep heatmap (heuristic CSR over difficulty grid).
"""
import json
import sys

sys.path.insert(0, "/home/z/my-project/cyberwarenv")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RUNS = "/home/z/my-project/cyberwarenv_runs"
OUT = "/home/z/my-project/download/figures"
import os
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.size": 11, "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 150, "savefig.dpi": 150, "axes.spines.top": False,
    "axes.spines.right": False,
})

CELLS = [
    ("corporate/scripted/DQN", "DQN — Corporate (S2)", 0.826, "#1f77b4"),
    ("corporate/scripted/PPO", "PPO — Corporate (S2)", 0.851, "#ff7f0e"),
    ("datacenter/adaptive/DQN", "DQN — DataCenter (S4)", 0.689, "#2ca02c"),
    ("datacenter/adaptive/PPO", "PPO — DataCenter (S4)", None, "#d62728"),
]


def load_runs_from_dirs():
    """Load curves + run data directly from run dirs (source of truth)."""
    import glob as _glob
    cells = {}
    for exp_dir in sorted(_glob.glob(f"{RUNS}/EXP-2026-*")):
        for run_dir in sorted(_glob.glob(f"{exp_dir}/run_*")):
            try:
                with open(f"{run_dir}/config.json", encoding="utf-8") as f:
                    cfg = json.load(f)
                with open(f"{run_dir}/results.json", encoding="utf-8") as f:
                    rres = json.load(f)
                if rres.get("status") != "COMPLETE":
                    continue
                key = f"{cfg['env_config']['scenario']}/{cfg['env_config']['attacker']}/{cfg['algorithm']}"
                cells.setdefault(key, []).append({
                    "seed": cfg["seed"],
                    "csr": rres["eval_summary"]["csr_mean"],
                    "steps": rres["csr_curve"]["steps"],
                    "curve": rres["csr_curve"]["csr"],
                })
            except Exception:
                continue
    return cells


def fig_training_curves(cells):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    panels = {"corporate/scripted/DQN": 0, "corporate/scripted/PPO": 0,
              "datacenter/adaptive/DQN": 1, "datacenter/adaptive/PPO": 1}
    for key, panel in panels.items():
        label, claim, color = None, None, None
        for k, lb, cl, c in CELLS:
            if k == key:
                label, claim, color = lb, cl, c
        runs = cells[key]
        steps = runs[0]["steps"]
        mat = np.array([r["curve"] for r in runs])
        mean, sd = mat.mean(axis=0), mat.std(axis=0)
        ax = axes[panel]
        ax.plot(steps, mean, "-o", ms=3, color=color,
                label=f"{label} (mean of {len(runs)} seeds)")
        ax.fill_between(steps, mean - sd, mean + sd, color=color, alpha=0.18,
                        label="±1 SD across seeds")
        if claim is not None:
            ax.axhline(claim, color="k", ls="--", lw=1.2,
                       label=f"Paper legacy claim = {claim:.1%}")
        ax.set_title(label, fontsize=11)
        ax.set_xlabel("Training steps")
        ax.set_ylabel("Evaluation Containment Success Rate")
        ax.set_ylim(-0.03, 1.06)
        ax.legend(fontsize=8, loc="lower right")
    fig.suptitle("Training curves: evaluation CSR vs training steps (100k budget, 5 seeds)",
                 fontsize=12)
    fig.savefig(f"{OUT}/fig_training_curves.png")
    plt.close(fig)


def fig_csr_comparison(summary):
    fig, ax = plt.subplots(figsize=(9.5, 5), constrained_layout=True)
    y = np.arange(len(CELLS))
    for i, (key, label, claim, color) in enumerate(CELLS):
        st = summary["cell_statistics"][key]
        m = st["run_csr_mean"]
        lo, hi = st["episode_pooled_ci"]["ci_low"], st["episode_pooled_ci"]["ci_high"]
        ax.barh(i, m, color=color, alpha=0.75, height=0.55)
        ax.plot([lo, hi], [i, i], color="k", lw=2)
        ax.plot([lo, lo], [i - 0.12, i + 0.12], color="k", lw=2)
        ax.plot([hi, hi], [i - 0.12, i + 0.12], color="k", lw=2)
        ax.text(hi + 0.015, i, f"{m:.1%}", va="center", fontsize=10)
        if claim is not None:
            ax.axvline(claim, color="gray", ls=":", lw=1.4)
            ax.text(claim, i + 0.36, f"claim {claim:.1%}", fontsize=8,
                    ha="center", color="dimgray")
    ax.set_yticks(y)
    ax.set_yticklabels([c[1] for c in CELLS])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("Containment Success Rate (100 eval episodes/run, pooled 95% CI)")
    ax.set_title("Final containment performance vs paper legacy claims")
    fig.savefig(f"{OUT}/fig_csr_comparison.png")
    plt.close(fig)


def fig_calibration():
    with open(f"{RUNS}/calibration_profile.json", encoding="utf-8") as f:
        cal = json.load(f)
    sweep = cal["full_sweep"]
    freqs = sorted({s["attack_frequency"] for s in sweep})
    succs = sorted({s["attack_success_base"] for s in sweep})
    grid = np.full((len(succs), len(freqs)), np.nan)
    for s in sweep:
        i = succs.index(s["attack_success_base"])
        j = freqs.index(s["attack_frequency"])
        grid[i, j] = s["heuristic_csr"]
    fig, ax = plt.subplots(figsize=(7, 4.6), constrained_layout=True)
    im = ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto", origin="lower")
    ax.set_xticks(range(len(freqs)), [f"{f:.2f}" for f in freqs])
    ax.set_yticks(range(len(succs)), [f"{s:.2f}" for s in succs])
    ax.set_xlabel("attack_frequency")
    ax.set_ylabel("attack_success_base")
    for i in range(len(succs)):
        for j in range(len(freqs)):
            ax.text(j, i, f"{grid[i,j]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title("Figure — Calibration sweep: heuristic-defender CSR over difficulty grid\n(chosen profile: lowest freq/succ within the learnable band)")
    fig.colorbar(im, ax=ax, label="Heuristic CSR")
    fig.savefig(f"{OUT}/fig_calibration.png")
    plt.close(fig)


def main():
    cells = load_runs_from_dirs()
    with open(f"{RUNS}/analysis_summary.json", encoding="utf-8") as f:
        summary = json.load(f)
    fig_training_curves(cells)
    fig_csr_comparison(summary)
    fig_calibration()
    print(f"[saved] 3 figures -> {OUT}")


if __name__ == "__main__":
    main()
