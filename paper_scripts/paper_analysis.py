#!/usr/bin/env python3
"""Full statistical battery for the CyberWarEnv factorial study.

Reads every COMPLETE run under cyberwarenv_runs/EXP-2026-*, groups by
(scenario, attacker, algorithm), and computes per-cell and pooled statistics.
Outputs paper_analysis.json used by the paper and figures.

SELECTION PROTOCOL (deterministic): the paper's canonical dataset is the
released 80-run registry snapshot. Runs of the interrupted pre-reset
expansion generation (torch 2.14.0+cpu, 2026-09-03) are excluded — they are
absent from the released registry — and among the remaining generations
(originals 2.14.0+cu130, factorial extension 2.14.1+cpu) exactly ONE run per
(cell, algorithm, seed) is kept: the FIRST by created_utc, directory path as
tie-break. (Verified: every duplicate re-run reproduces the same per-seed
CSR, so the selection rule does not change any reported value — see
scripts/verify_paper_provenance.py.)

Everything here is computed from run artifacts. Nothing is assumed.
"""
import glob
import itertools
import json

import numpy as np
from scipy import stats

RUNS = "/home/z/my-project/cyberwarenv_runs"
OUT = f"{RUNS}/paper_analysis.json"


def load_all():
    runs = {}
    for run_dir in sorted(glob.glob(f"{RUNS}/EXP-2026-*/run_*")):
        try:
            cfg = json.load(open(f"{run_dir}/config.json", encoding="utf-8"))
            res = json.load(open(f"{run_dir}/results.json", encoding="utf-8"))
            if res.get("status") != "COMPLETE":
                continue
            if cfg.get("software_versions", {}).get("torch") == "2.14.0+cpu":
                continue  # excluded expansion generation (not in released registry)
            key = f"{cfg['env_config']['scenario']}/{cfg['env_config']['attacker']}/{cfg['algorithm']}"
            runs.setdefault(key, []).append({
                "run_id": cfg["run_id"],
                "experiment_id": cfg["experiment_id"],
                "seed": cfg["seed"],
                "csr": res["eval_summary"]["csr_mean"],
                "csr_episodes": res["eval"]["csr"],
                "containment_time": res["eval_summary"]["containment_time_mean"],
                "nodes_max": res["eval_summary"]["nodes_compromised_max_mean"],
                "curve_steps": res["csr_curve"]["steps"],
                "curve_csr": res["csr_curve"]["csr"],
                "created": cfg.get("created_utc", ""),
                "dir": run_dir,
            })
        except Exception:
            continue
    # Deduplicate: one run per (cell, algorithm, seed) — earliest created_utc,
    # directory path as deterministic tie-break (see docstring).
    for k in runs:
        best = {}
        for r in runs[k]:
            s = r["seed"]
            if s not in best or (r["created"], r["dir"]) < (best[s]["created"], best[s]["dir"]):
                best[s] = r
        runs[k] = sorted(best.values(), key=lambda r: r["seed"])
    return runs


def wilson(episodes, z=1.96):
    n = len(episodes)
    p = float(np.mean(episodes))
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return [round(centre - half, 4), round(centre + half, 4)]


def hedges_g(a, b):
    """Hedges' g with small-sample correction (independent-form, pooled SD)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    sa, sb = a.std(ddof=1), b.std(ddof=1)
    sp = np.sqrt(((na - 1) * sa**2 + (nb - 1) * sb**2) / (na + nb - 2))
    if sp == 0:
        return 0.0
    d = (a.mean() - b.mean()) / sp
    J = 1 - 3 / (4 * (na + nb) - 9)
    return round(float(d * J), 3)


def exact_wilcoxon(x, y):
    """Exact two-sided Wilcoxon signed-rank on paired samples."""
    d = np.asarray(x, float) - np.asarray(y, float)
    nz = d[d != 0]
    n = len(nz)
    if n == 0:
        return None, n
    w = stats.wilcoxon(nz, alternative="two-sided", mode="exact")
    return float(w.pvalue), n


def rank_biserial(x, y):
    d = np.asarray(x, float) - np.asarray(y, float)
    d = d[d != 0]
    r = stats.rankdata(np.abs(d))
    wplus = r[d > 0].sum()
    n = len(d)
    return round(float((2 * wplus - n * (n + 1) / 2) / (n * (n + 1) / 2)), 3)


def holm(pvals):
    """Holm step-down adjusted p-values (monotonicity enforced)."""
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    prev = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, pvals[idx] * (m - rank))
        prev = max(prev, val)
        adj[idx] = prev
    return [round(float(a), 6) for a in adj]


def main():
    runs = load_all()
    cells = ["corporate/scripted", "corporate/adaptive",
             "datacenter/scripted", "datacenter/adaptive"]
    out = {"n_runs_total": sum(len(v) for v in runs.values()),
           "cells": {}, "pooling_note": "computed from run artifacts only"}

    for cell in cells:
        ppo = runs.get(f"{cell}/PPO", [])
        dqn = runs.get(f"{cell}/DQN", [])
        entry = {}
        for name, rr in (("PPO", ppo), ("DQN", dqn)):
            if not rr:
                continue
            eps = list(itertools.chain.from_iterable(r["csr_episodes"] for r in rr))
            entry[name] = {
                "n_runs": len(rr),
                "seeds": [r["seed"] for r in rr],
                "per_run_csr": [round(r["csr"], 4) for r in rr],
                "csr_mean": round(float(np.mean([r["csr"] for r in rr])), 4),
                "csr_sd": round(float(np.std([r["csr"] for r in rr], ddof=1)), 4) if len(rr) > 1 else None,
                "wilson_pooled": wilson(eps),
                "episodes": len(eps),
                "containment_time_mean": round(float(np.mean([r["containment_time"] for r in rr])), 2),
                "nodes_max_mean": round(float(np.mean([r["nodes_max"] for r in rr])), 3),
                "experiment_ids": sorted({r["experiment_id"] for r in rr}),
                "curves": {"steps": rr[0]["curve_steps"],
                           "per_seed": [r["curve_csr"] for r in rr]},
            }
        if ppo and dqn and len(ppo) == len(dqn):
            paired = [(p, d) for p, d in zip(ppo, dqn) if p["seed"] == d["seed"]]
            if paired:
                x = [float(p["csr"]) for p, _ in paired]
                y = [float(d["csr"]) for _, d in paired]
                pval, n_pairs = exact_wilcoxon(x, y)
                entry["comparison"] = {
                    "n_pairs": n_pairs,
                    "delta_mean": round(float(np.mean(x) - np.mean(y)), 4),
                    "wilcoxon_exact_p": pval,
                    "wilcoxon_floor_note": f"exact floor for n={n_pairs} two-sided is {2**-(n_pairs-1):.6f}" if n_pairs else None,
                    "hedges_g": hedges_g(x, y),
                    "rank_biserial": rank_biserial(x, y),
                    "wins_ppo": int(sum(1 for a, b in zip(x, y) if a > b)),
                    "wins_dqn": int(sum(1 for a, b in zip(x, y) if a < b)),
                    "mannwhitney_exact_p": (lambda w: float(w.pvalue) if w is not None else None)(
                        stats.mannwhitneyu(x, y, alternative="two-sided", method="exact")
                        if len(set(x + y)) == len(x + y) else
                        stats.mannwhitneyu(x, y, alternative="two-sided")),
                }
        out["cells"][cell] = entry

    # Holm correction across cells that have comparisons
    ps = [(c, out["cells"][c]["comparison"]["wilcoxon_exact_p"])
          for c in cells if out["cells"][c].get("comparison")
          and out["cells"][c]["comparison"]["wilcoxon_exact_p"] is not None]
    if ps:
        raw = [p for _, p in ps]
        adj = holm(raw)
        for (c, _), a in zip(ps, adj):
            out["cells"][c]["comparison"]["holm_adjusted_p"] = a

    # Global sensitivity: pool seed-paired differences across all cells (same seeds)
    pools_x, pools_y = [], []
    for cell in cells:
        ppo = runs.get(f"{cell}/PPO", [])
        dqn = runs.get(f"{cell}/DQN", [])
        common = sorted(set(r["seed"] for r in ppo) & set(r["seed"] for r in dqn))
        pm = {r["seed"]: r["csr"] for r in ppo}
        dm = {r["seed"]: r["csr"] for r in dqn}
        for s in common:
            pools_x.append(pm[s])
            pools_y.append(dm[s])
    if pools_x:
        pval, n = exact_wilcoxon(pools_x, pools_y)
        out["global_pooled"] = {
            "n_pairs": n,
            "wilcoxon_exact_p": pval,
            "hedges_g": hedges_g(pools_x, pools_y),
            "wins_ppo": int(sum(1 for a, b in zip(pools_x, pools_y) if a > b)),
            "wins_dqn": int(sum(1 for a, b in zip(pools_x, pools_y) if a < b)),
            "ties": int(sum(1 for a, b in zip(pools_x, pools_y) if a == b)),
        }

    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    # console summary
    print(f"total COMPLETE runs: {out['n_runs_total']}")
    for c in cells:
        e = out["cells"].get(c, {})
        p, d = e.get("PPO", {}), e.get("DQN", {})
        line = f"{c:26s} PPO={p.get('csr_mean','-')} (n={p.get('n_runs','-')})  DQN={d.get('csr_mean','-')} (n={d.get('n_runs','-')})"
        comp = e.get("comparison", {})
        if comp:
            line += f" | p={comp.get('wilcoxon_exact_p')} holm={comp.get('holm_adjusted_p','-')} g={comp.get('hedges_g')}"
        print(line)
    if out.get("global_pooled"):
        g = out["global_pooled"]
        print(f"GLOBAL pooled: n={g['n_pairs']} pairs, PPO wins {g['wins_ppo']}, "
              f"DQN wins {g['wins_dqn']}, ties {g['ties']}, exact p={g['wilcoxon_exact_p']}, g={g['hedges_g']}")


if __name__ == "__main__":
    main()
