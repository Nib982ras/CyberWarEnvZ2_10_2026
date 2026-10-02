#!/usr/bin/env python3
"""Paper figures for the CyberWarEnv factorial study.

All data loaded from run artifacts + calibration_profile.json.
No embedded titles (captions live in the paper), no claim reference lines.
"""
import glob
import itertools
import json
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RUNS = "/home/z/my-project/cyberwarenv_runs"
OUT = "/home/z/my-project/download/CyberWarEnv_Q1_Paper/figures"
import os
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 150, "savefig.dpi": 150, "axes.spines.top": False,
    "axes.spines.right": False,
    "font.family": "DejaVu Sans",
})

C_PPO = "#d95f02"
C_DQN = "#1b6ca8"
C_RAND = "#8a8a8a"
C_HEUR = "#2e7d32"


def load_runs():
    """Load the paper's canonical 80 runs (see paper_analysis.py protocol).

    Excludes the interrupted pre-reset expansion generation (torch
    2.14.0+cpu, 2026-09-03) which is absent from the released registry;
    then keeps the earliest completed run per (cell, algorithm, seed).
    """
    runs = defaultdict(list)
    for run_dir in sorted(glob.glob(f"{RUNS}/EXP-2026-*/run_*")):
        try:
            cfg = json.load(open(f"{run_dir}/config.json", encoding="utf-8"))
            res = json.load(open(f"{run_dir}/results.json", encoding="utf-8"))
            if res.get("status") != "COMPLETE":
                continue
            if cfg.get("software_versions", {}).get("torch") == "2.14.0+cpu":
                continue  # excluded expansion generation (not in released registry)
            key = (cfg["env_config"]["scenario"], cfg["env_config"]["attacker"],
                   cfg["algorithm"])
            runs[key].append({
                "seed": cfg["seed"],
                "csr": res["eval_summary"]["csr_mean"],
                "steps": res["csr_curve"]["steps"],
                "curve": res["csr_curve"]["csr"],
                "created": cfg.get("created_utc", ""),
                "dir": run_dir,
            })
        except Exception:
            continue
    for key in runs:
        best = {}
        for r in runs[key]:
            s = r["seed"]
            if s not in best or (r["created"], r["dir"]) < (best[s]["created"], best[s]["dir"]):
                best[s] = r
        runs[key] = sorted(best.values(), key=lambda r: r["seed"])
    return runs


def wilson(episodes, z=1.96):
    n = len(episodes)
    p = float(np.mean(episodes))
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def cell_means(runs, scenario, attacker, alg):
    rr = runs.get((scenario, attacker, alg), [])
    return [r["csr"] for r in rr]


def fig_training(runs):
    """Two panels (corporate, datacenter): mean eval-CSR curves, 4 lines each."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), constrained_layout=True)
    for ax, scen in zip(axes, ["corporate", "datacenter"]):
        for alg, color in (("PPO", C_PPO), ("DQN", C_DQN)):
            for att, ls in (("scripted", "-"), ("adaptive", "--")):
                rr = runs.get((scen, att, alg), [])
                if not rr:
                    continue
                curves = np.array([r["curve"] for r in rr], dtype=float)
                steps = rr[0]["steps"]
                ax.plot(steps, curves.mean(axis=0), ls, color=color, lw=1.8,
                        label=f"{alg} / {att} (n={len(rr)})")
                ax.plot(steps, curves.T, color=color, alpha=0.10, lw=0.7)
        ax.set_title(scen.capitalize(), fontsize=10)
        ax.set_xlabel("Training steps")
        ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("Evaluation CSR")
    axes[0].legend(fontsize=7.5, loc="lower right", framealpha=0.9)
    fig.savefig(f"{OUT}/fig_training_curves.png")
    plt.close(fig)
    print("fig_training_curves.png done")


def fig_csr(runs):
    """Two panels: per operating point, bars for the two cells x two algorithms
    with episode-pooled Wilson CIs, plus measured baseline lines."""
    cal = json.load(open(f"{RUNS}/calibration_profile.json", encoding="utf-8"))
    base = {
        "corporate": (cal["stage2_corporate"]["random_csr_at_calibration"],
                      cal["stage2_corporate"]["heuristic_csr_at_calibration"]),
        "datacenter": (cal["stage4_random_csr"], cal["stage4_heuristic_csr"]),
    }
    # pooled episode outcomes per (scenario, attacker, alg) — canonical
    # selection: exclude the pre-reset expansion generation (torch
    # 2.14.0+cpu) and keep the earliest completed run per seed, exactly as
    # in load_runs() / paper_analysis.py.
    pooled = {}
    for run_dir in sorted(glob.glob(f"{RUNS}/EXP-2026-*/run_*")):
        try:
            cfg = json.load(open(f"{run_dir}/config.json", encoding="utf-8"))
            res = json.load(open(f"{run_dir}/results.json", encoding="utf-8"))
            if res.get("status") != "COMPLETE":
                continue
            if cfg.get("software_versions", {}).get("torch") == "2.14.0+cpu":
                continue  # excluded expansion generation (not in released registry)
            key = (cfg["env_config"]["scenario"], cfg["env_config"]["attacker"],
                   cfg["algorithm"])
            pooled.setdefault(key, []).append({
                "seed": cfg["seed"],
                "episodes": res["eval"]["csr"],
                "created": cfg.get("created_utc", ""),
                "dir": run_dir,
            })
        except Exception:
            continue
    for key in pooled:
        best = {}
        for r in pooled[key]:
            s = r["seed"]
            if s not in best or (r["created"], r["dir"]) < (best[s]["created"], best[s]["dir"]):
                best[s] = r
        pooled[key] = sorted(best.values(), key=lambda r: r["seed"])
    pooled_episodes = {key: list(itertools.chain.from_iterable(
        r["episodes"] for r in rr)) for key, rr in pooled.items()}
    # keep downstream code shape: pooled[key] is a flat episode list
    pooled = pooled_episodes

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), constrained_layout=True,
                             sharey=True)
    order = [("corporate", [("scripted", "Corp. / Scripted"),
                            ("adaptive", "Corp. / Adaptive")]),
             ("datacenter", [("scripted", "DC / Scripted"),
                             ("adaptive", "DC / Adaptive")])]
    for ax, (scen, cells) in zip(axes, order):
        yticks, ylabels = [], []
        for j, (att, label) in enumerate(cells):
            for k, (alg, color) in enumerate((("DQN", C_DQN), ("PPO", C_PPO))):
                eps = pooled.get((scen, att, alg), [])
                if not eps:
                    continue
                mean = float(np.mean(eps))
                lo, hi = wilson(eps)
                y = j + (0.18 if alg == "PPO" else -0.18)
                ax.barh(y, mean, height=0.30, color=color, alpha=0.85)
                ax.plot([lo, hi], [y, y], color="k", lw=1.1)
                ax.plot([mean], [y], "k|", markersize=6)
                yticks.append(y)
                ylabels.append(label if k == 0 else "")
        rb, hb = base[scen]
        ax.axvline(rb, color=C_RAND, ls=":", lw=1.4)
        ax.axvline(hb, color=C_HEUR, ls=":", lw=1.4)
        ax.text(rb, 1.62, "random", rotation=90, fontsize=7.5, color=C_RAND,
                ha="right", va="top")
        ax.text(hb, 1.62, "heuristic", rotation=90, fontsize=7.5, color=C_HEUR,
                ha="right", va="top")
        ax.set_yticks([-0.18, 0.18, 0.82, 1.18])
        ax.set_yticklabels(["DQN", "PPO", "DQN", "PPO"], fontsize=8.5)
        ax.set_title(scen.capitalize(), fontsize=10)
        ax.set_xlim(0, 1.0)
        ax.set_ylim(-0.55, 1.75)
    axes[0].set_xlabel("CSR")
    axes[1].set_xlabel("CSR")
    fig.savefig(f"{OUT}/fig_csr_comparison.png")
    plt.close(fig)
    print("fig_csr_comparison.png done")


def fig_calibration():
    """Calibration sweep: random vs heuristic CSR across the 12 swept cells."""
    cal = json.load(open(f"{RUNS}/calibration_profile.json", encoding="utf-8"))
    sweep = cal["full_sweep"]
    fig, ax = plt.subplots(figsize=(3.5, 2.9), constrained_layout=True)
    freqs = sorted({c["attack_frequency"] for c in sweep})
    succs = sorted({c["attack_success_base"] for c in sweep})
    for c in sweep:
        x = c["attack_frequency"] + (0.018 * succs.index(c["attack_success_base"]) - 0.018)
        ax.plot(x, c["random_csr"], "o", color=C_RAND, ms=5)
        ax.plot(x, c["heuristic_csr"], "s", color=C_HEUR, ms=5)
        ax.plot([x, x], [c["random_csr"], c["heuristic_csr"]], color="#c9c9c9",
                lw=0.8, zorder=0)
    # operating points
    s2 = cal["stage2_corporate"]
    ax.plot([s2["attack_frequency"]], [s2["random_csr_at_calibration"]], "*",
            color="#111111", ms=11, zorder=5)
    ax.plot([s2["attack_frequency"]], [s2["heuristic_csr_at_calibration"]], "*",
            color="#111111", ms=11, zorder=5)
    ax.plot([0.55], [cal["stage4_random_csr"]], "*", color="#111111", ms=11, zorder=5)
    ax.plot([0.55], [cal["stage4_heuristic_csr"]], "*", color="#111111", ms=11, zorder=5)
    ax.set_xlabel("Attack frequency")
    ax.set_ylabel("Defender CSR")
    ax.set_ylim(-0.03, 0.80)
    handles = [
        plt.Line2D([], [], marker="o", color=C_RAND, linestyle="", label="Random defender"),
        plt.Line2D([], [], marker="s", color=C_HEUR, linestyle="", label="Heuristic defender"),
        plt.Line2D([], [], marker="*", color="#111111", linestyle="", label="Selected operating point"),
    ]
    ax.legend(handles=handles, fontsize=7.5, loc="upper right", framealpha=0.9)
    fig.savefig(f"{OUT}/fig_calibration.png")
    plt.close(fig)
    print("fig_calibration.png done")


def main():
    runs = load_runs()
    n = sum(len(v) for v in runs.values())
    print(f"loaded {n} runs across {len(runs)} cell-alg groups")
    fig_training(runs)
    fig_csr(runs)
    fig_calibration()


if __name__ == "__main__":
    main()
