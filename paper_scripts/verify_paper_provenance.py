#!/usr/bin/env python3
"""Reverse-match the shipped paper_analysis.json against on-disk runs.

For every (cell, algorithm, seed) the shipped JSON records per_run_csr.
The registry may contain duplicate runs of the same (cell, seed) from the
interrupted power-expansion session. This tool determines, per seed, WHICH
on-disk run the shipped statistics came from, and tests whether a simple
deterministic rule reproduces the shipped selection for all 80 seeds.

Exit 0 + "PROVENANCE RULE PROVEN" if one rule explains all 80 picks.
"""
import glob
import json
import sys

RUNS = "/home/z/my-project/cyberwarenv_runs"
SHIPPED = "/tmp/paper_analysis_SHIPPED.json"

TOL = 1e-6


def load_runs():
    runs = []
    for rd in sorted(glob.glob(f"{RUNS}/EXP-2026-*/run_*")):
        try:
            cfg = json.load(open(f"{rd}/config.json", encoding="utf-8"))
            res = json.load(open(f"{rd}/results.json", encoding="utf-8"))
        except Exception:
            continue
        if res.get("status") != "COMPLETE":
            continue
        csr = res.get("eval_summary", {}).get("csr_mean")
        runs.append({
            "dir": rd,
            "exp": rd.split("/EXP-2026-")[1][:6],
            "run": rd.split("/")[-1],
            "cell": f"{cfg['env_config']['scenario']}/{cfg['env_config']['attacker']}",
            "alg": cfg["algorithm"],
            "seed": cfg["seed"],
            "csr": csr,
            "created": cfg.get("created_utc", res.get("created_utc", "")),
            "finished": res.get("finished_utc", ""),
        })
    return runs


def main():
    shipped = json.load(open(SHIPPED, encoding="utf-8"))
    runs = load_runs()
    print(f"shipped: n_runs_total={shipped['n_runs_total']}  disk COMPLETE runs={len(runs)}")

    rules = {"earliest_created": 0, "latest_created": 0, "lowest_exp": 0, "no_candidate": 0}
    mismatches = []
    for cell, algs in shipped["cells"].items():
        for alg in ("PPO", "DQN"):
            info = algs[alg]
            for seed, csr in zip(info["seeds"], info["per_run_csr"]):
                cands = [r for r in runs if r["cell"] == cell and r["alg"] == alg and r["seed"] == seed]
                match = [r for r in cands if abs(r["csr"] - csr) < TOL]
                if not match:
                    mismatches.append((cell, alg, seed, csr, "NO MATCHING CSR ON DISK", cands))
                    rules["no_candidate"] += 1
                    continue
                if len(match) > 1:
                    mismatches.append((cell, alg, seed, csr, "AMBIGUOUS", match))
                # which rule picks the matched one?
                by_created = sorted(cands, key=lambda r: (r["created"], r["finished"], r["dir"]))
                if abs(by_created[0]["csr"] - csr) < TOL:
                    rules["earliest_created"] += 1
                if abs(by_created[-1]["csr"] - csr) < TOL:
                    rules["latest_created"] += 1
                by_exp = sorted(cands, key=lambda r: (r["exp"], r["run"]))
                if abs(by_exp[0]["csr"] - csr) < TOL:
                    rules["lowest_exp"] += 1

    print("rule scores (out of 80):", rules)
    real_mism = [m for m in mismatches if m[4] == "NO MATCHING CSR ON DISK"]
    ambigu = [m for m in mismatches if m[4] == "AMBIGUOUS"]
    print(f"unmatched seeds: {len(real_mism)}   ambiguous seeds (dup csr): {len(ambigu)}")
    for cell, alg, seed, csr, why, cands in real_mism[:8]:
        print(f"  UNMATCHED {cell}/{alg} seed={seed} shipped_csr={csr}")
        for c in cands:
            print(f"      disk: {c['exp']}/{c['run']} csr={c['csr']} created={c['created']}")
    for cell, alg, seed, csr, why, cands in ambigu[:6]:
        exps = [(c['exp'], c['run'], c['csr'], c['created']) for c in cands]
        print(f"  AMBIGUOUS {cell}/{alg} seed={seed} csr={csr}: {exps}")

    best = max(rules, key=rules.get)
    if rules[best] == 80 and not real_mism:
        print(f"PROVENANCE RULE PROVEN: {best} explains all 80 shipped picks")
        sys.exit(0)
    else:
        print("NO single rule proven — investigate above")
        sys.exit(1)


if __name__ == "__main__":
    main()
