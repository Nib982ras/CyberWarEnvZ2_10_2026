"""Aggregate verification results, run statistical tests, and compare
against the paper's legacy claims. Produces analysis_summary.json and
the CSV table for the report."""
import json
import glob as _glob
import sys

sys.path.insert(0, "/home/z/my-project/cyberwarenv")

import numpy as np
import pandas as pd

from cyberwarenv import (bootstrap_ci, mann_whitney_test, wilcoxon_test,
                         cohens_d, rank_biserial, holm_bonferroni,
                         verify_against_claim, descriptive)

RUNS = "/home/z/my-project/cyberwarenv_runs"


def load_from_run_dirs():
    """Rebuild the full results structure directly from run directories
    (robust against batch summary overwrites)."""
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
                algo = cfg["algorithm"]
                seed = cfg["seed"]
                scen = cfg["env_config"]["scenario"]
                att = cfg["env_config"]["attacker"]
                key = f"{scen}/{att}/{algo}"
                cells.setdefault(key, {
                    "runs": [],
                    "difficulty": cfg["env_config"],
                    "claim": {"corporate/scripted/DQN": 0.826,
                              "corporate/scripted/PPO": 0.851,
                              "datacenter/adaptive/DQN": 0.689,
                              "datacenter/adaptive/PPO": None}.get(key),
                })["runs"].append({
                    "seed": seed,
                    "csr": rres["eval_summary"]["csr_mean"],
                    "csr_episodes": rres["eval"]["csr"],
                    "run_id": cfg["run_id"],
                    "artifact_hash": rres.get("artifact_hash", ""),
                    "containment_time": rres["eval_summary"]["containment_time_mean"],
                    "nodes_max": rres["eval_summary"]["nodes_compromised_max_mean"],
                    "run_dir": run_dir,
                })
            except Exception as e:
                print(f"[warn] skipping {run_dir}: {e}")
    return cells


def main():
    # rebuild directly from run directories (source of truth)
    res = load_from_run_dirs()
    data = {"experiment_id": "EXP-2026-000001+000002",
            "train_steps": 100_000, "seeds": [0, 1, 2, 3, 4],
            "eval_episodes": 100, "results": res}

    rows = []
    cell_stats = {}
    for key, cell in res.items():
        csrs = [r["csr"] for r in cell["runs"]]
        ctimes = [r["containment_time"] for r in cell["runs"]]
        nmax = [r["nodes_max"] for r in cell["runs"]]
        # pooled episode-level bootstrap CI
        pooled = [v for r in cell["runs"] for v in r["csr_episodes"]]
        epi_ci = bootstrap_ci(pooled, n_resamples=10000, seed=42)
        run_ci = bootstrap_ci(csrs, n_resamples=10000, seed=42)
        wilson = _wilson(pooled)
        cell_stats[key] = {
            "claim": cell["claim"],
            "run_csr_mean": float(np.mean(csrs)),
            "run_csr_sd": float(np.std(csrs, ddof=1)) if len(csrs) > 1 else 0.0,
            "run_ci": run_ci,
            "episode_pooled_ci": epi_ci,
            "wilson_ci": wilson,
            "containment_time_mean": float(np.mean(ctimes)),
            "nodes_compromised_max_mean": float(np.mean(nmax)),
            "n_runs": len(csrs),
            "episodes_per_run": len(pooled) // len(csrs),
        }
        for r in cell["runs"]:
            rows.append({"cell": key, "seed": r["seed"], "csr": r["csr"],
                         "containment_time": r["containment_time"],
                         "nodes_max": r["nodes_max"],
                         "run_id": r["run_id"],
                         "artifact_hash": r["artifact_hash"][:16]})

    df = pd.DataFrame(rows)
    df.to_csv(f"{RUNS}/verification_runs_table.csv", index=False)

    # ---------------- verification vs legacy claims ----------------
    claims = []
    for key, st in cell_stats.items():
        if st["claim"] is not None:
            verdict = verify_against_claim([st["episode_pooled_ci"]], st["claim"])
            claims.append({"cell": key, "claimed": st["claim"],
                           "measured": st["run_csr_mean"], **verdict})

    # ---------------- statistical comparisons (pre-registered) ----------------
    tests = []
    pvals = []
    if "corporate/scripted/DQN" in res and "corporate/scripted/PPO" in res:
        dqn = [r["csr"] for r in res["corporate/scripted/DQN"]["runs"]]
        ppo = [r["csr"] for r in res["corporate/scripted/PPO"]["runs"]]
        t1 = wilcoxon_test(dqn, ppo)          # paired by seed
        t2 = mann_whitney_test(dqn, ppo)      # unpaired
        tests.append({"comparison": "DQN vs PPO (corporate/S2)",
                      "dqn_mean": float(np.mean(dqn)), "ppo_mean": float(np.mean(ppo)),
                      "cohens_d": cohens_d(dqn, ppo),
                      "rank_biserial": rank_biserial(dqn, ppo),
                      "wilcoxon_paired": t1, "mann_whitney": t2})
        pvals.append(t2.get("p_value", 1.0))
    if "datacenter/adaptive/DQN" in res and "datacenter/adaptive/PPO" in res:
        dqn = [r["csr"] for r in res["datacenter/adaptive/DQN"]["runs"]]
        ppo = [r["csr"] for r in res["datacenter/adaptive/PPO"]["runs"]]
        t2 = mann_whitney_test(dqn, ppo)
        tests.append({"comparison": "DQN vs PPO (datacenter/S4)",
                      "dqn_mean": float(np.mean(dqn)), "ppo_mean": float(np.mean(ppo)),
                      "cohens_d": cohens_d(dqn, ppo),
                      "rank_biserial": rank_biserial(dqn, ppo),
                      "mann_whitney": t2})
        pvals.append(t2.get("p_value", 1.0))
    # Holm-Bonferroni across the family of comparisons
    if pvals:
        hb = holm_bonferroni(pvals)
        for i, t in enumerate(tests):
            t["holm_adjusted_p"] = hb["adjusted_p"][i]
            t["significant"] = hb["reject_null"][i]

    summary = {
        "experiment_id": data["experiment_id"],
        "train_steps": data["train_steps"],
        "seeds": data["seeds"],
        "eval_episodes_per_run": data["eval_episodes"],
        "cell_statistics": cell_stats,
        "claim_verification": claims,
        "statistical_tests": tests,
    }
    with open(f"{RUNS}/analysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ---------------- console report ----------------
    print("=" * 78)
    print(f"VERIFICATION ANALYSIS — experiment {data['experiment_id']}")
    print("=" * 78)
    for key, st in cell_stats.items():
        print(f"\n{key}")
        print(f"  runs={st['n_runs']}  CSR mean={st['run_csr_mean']:.3f} "
              f"SD={st['run_csr_sd']:.3f}")
        print(f"  run-level CI95=[{st['run_ci']['ci_low']:.3f}, {st['run_ci']['ci_high']:.3f}]")
        print(f"  episode-level CI95=[{st['episode_pooled_ci']['ci_low']:.3f}, "
              f"{st['episode_pooled_ci']['ci_high']:.3f}]")
        print(f"  containment_time={st['containment_time_mean']:.1f} steps | "
              f"nodes_max={st['nodes_compromised_max_mean']:.1f}")
    print("\n--- CLAIM VERDICTS ---")
    for c in claims:
        print(f"  {c['cell']}: claimed={c['claimed']:.1%} measured={c['measured']:.1%} "
              f"-> {c['status']}")
    print("\n--- TESTS ---")
    for t in tests:
        print(f"  {t['comparison']}: d={t['cohens_d']:.2f} "
              f"p_raw={t['mann_whitney'].get('p_value', float('nan')):.4f} "
              f"p_holm={t.get('holm_adjusted_p', float('nan')):.4f}")
    print(f"\n[saved] {RUNS}/analysis_summary.json + verification_runs_table.csv")


def _wilson(values, z=1.96):
    n = len(values)
    p = float(np.mean(values))
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return [float(centre - half), float(centre + half)]


if __name__ == "__main__":
    main()
