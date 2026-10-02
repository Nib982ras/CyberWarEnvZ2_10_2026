"""Difficulty Calibration Sweep (Research Calibration Profile).

Principled selection criteria (documented BEFORE looking at results):
  C1. Random (no-defense) policy CSR <= 0.10   -> env non-trivial
  C2. Heuristic (rule-based) policy CSR in [0.55, 0.85] -> learnable, not saturated
  C3. Prefer the LOWEST attack_frequency meeting C1+C2, then the LOWEST
      attack_success_base (avoid inflating difficulty to force-match paper numbers)

The chosen profile is saved as the official Calibration Profile for the
verification experiments.
"""
import itertools
import json
import sys
import time

sys.path.insert(0, "/home/z/my-project/cyberwarenv")

import numpy as np
from cyberwarenv import CyberWarEnv, DifficultyProfile

ROOT = "/home/z/my-project/cyberwarenv_runs"


def rollout(env_factory, policy: str, episodes: int = 30, base_seed: int = 7):
    csr = []
    for ep in range(episodes):
        env = env_factory()
        obs, info = env.reset(seed=base_seed * 1000 + ep)
        done = False
        while not done:
            if policy == "random":
                action = int(env.action_space.sample())
            else:  # heuristic: constant Remediate (auto-targeted)
                action = 4
            obs, r, term, trunc, info = env.step(action)
            done = term or trunc
        csr.append(info["episode_metrics"]["containment_success"])
    return csr


def main():
    grid_freq = [0.45, 0.55, 0.65, 0.75]
    grid_succ = [0.62, 0.72, 0.82]
    results = []
    t0 = time.time()
    print("=" * 78)
    print("CALIBRATION SWEEP — corporate / scripted attacker (30 eps per cell)")
    print("Criteria: C1 random<=0.10 | C2 heuristic in [0.55,0.85] | C3 lowest freq,succ")
    print("=" * 78)
    for f, s in itertools.product(grid_freq, grid_succ):
        diff = DifficultyProfile(attack_frequency=f, attack_success_base=s)
        fac = lambda: CyberWarEnv("corporate", "scripted", diff, topology_seed=100)
        rnd = np.mean(rollout(fac, "random"))
        heu = np.mean(rollout(fac, "heuristic"))
        ok = (rnd <= 0.10) and (0.55 <= heu <= 0.85)
        results.append({"attack_frequency": f, "attack_success_base": s,
                        "random_csr": float(rnd), "heuristic_csr": float(heu),
                        "criteria_met": bool(ok)})
        print(f"freq={f:.2f} succ={s:.2f} | random={rnd:.3f} heuristic={heu:.3f} "
              f"| {'PASS' if ok else 'fail'}")

    passing = [r for r in results if r["criteria_met"]]
    if passing:
        passing.sort(key=lambda r: (r["attack_frequency"], r["attack_success_base"]))
        chosen = passing[0]
    else:
        # fallback: closest to band
        results.sort(key=lambda r: abs(r["heuristic_csr"] - 0.70))
        chosen = results[0]

    print("-" * 78)
    print(f"CHOSEN (corporate/stage2): freq={chosen['attack_frequency']} "
          f"succ={chosen['attack_success_base']} "
          f"(heuristic={chosen['heuristic_csr']:.3f})")

    # DataCenter Stage 4 profile: same base + stronger adaptive targeting
    diff4 = DifficultyProfile(
        attack_frequency=min(0.85, chosen["attack_frequency"] + 0.10),
        attack_success_base=min(0.85, chosen["attack_success_base"] + 0.05),
        adaptive_critical_weight=5.0,
    )
    fac4 = lambda: CyberWarEnv("datacenter", "adaptive", diff4, topology_seed=200)
    rnd4 = np.mean(rollout(fac4, "random"))
    heu4 = np.mean(rollout(fac4, "heuristic"))
    print(f"CHOSEN (datacenter/stage4): freq={diff4.attack_frequency} "
          f"succ={diff4.attack_success_base} | random={rnd4:.3f} heuristic={heu4:.3f}")

    profile = {
        "calibration_date": time.strftime("%Y-%m-%d"),
        "criteria": "C1 random<=0.10; C2 heuristic in [0.55,0.85]; C3 lowest freq then succ",
        "stage2_corporate": {
            "attack_frequency": chosen["attack_frequency"],
            "attack_success_base": chosen["attack_success_base"],
            "heuristic_csr_at_calibration": chosen["heuristic_csr"],
            "random_csr_at_calibration": chosen["random_csr"],
        },
        "stage4_datacenter": diff4.to_dict(),
        "stage4_random_csr": float(rnd4),
        "stage4_heuristic_csr": float(heu4),
        "full_sweep": results,
    }
    import os
    os.makedirs(ROOT, exist_ok=True)
    out = f"{ROOT}/calibration_profile.json"
    with open(out, "w", encoding="utf-8") as fjson:
        json.dump(profile, fjson, indent=2, ensure_ascii=False)
    print(f"[saved] {out}")
    print(f"[elapsed] {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
