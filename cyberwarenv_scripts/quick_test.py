"""Quick smoke test for the CyberWarEnv package."""
import sys, time
sys.path.insert(0, "/home/z/my-project/cyberwarenv")

import numpy as np
from cyberwarenv import (CyberWarEnv, DifficultyProfile, build_topology,
                         bootstrap_ci, descriptive)

def run_random_rollout(scenario, attacker_kind, seed=0, episodes=20):
    env = CyberWarEnv(scenario=scenario, attacker_kind=attacker_kind,
                      difficulty=DifficultyProfile(), topology_seed=100 + seed,
                      env_seed=seed)
    csr, rewards, nodes_max = [], [], []
    for ep in range(episodes):
        obs, info = env.reset(seed=seed * 1000 + ep)
        done = False
        while not done:
            action = env.action_space.sample()
            obs, r, term, trunc, info = env.step(action)
            done = term or trunc
        m = info["episode_metrics"]
        csr.append(m["containment_success"])
        rewards.append(m["cumulative_reward"])
        nodes_max.append(m["nodes_compromised_max"])
    return {"csr": csr, "rewards": rewards, "nodes_max": nodes_max}


def run_heuristic_rollout(scenario, attacker_kind, seed=0, episodes=20):
    """Rule-based SOC-analyst baseline: always issue the Remediate response.
    Auto-targeting routes it to the most-suspicious node."""
    env = CyberWarEnv(scenario=scenario, attacker_kind=attacker_kind,
                      difficulty=DifficultyProfile(), topology_seed=100 + seed,
                      env_seed=seed)
    csr, rewards, nodes_max = [], [], []
    for ep in range(episodes):
        obs, info = env.reset(seed=seed * 1000 + ep)
        done = False
        while not done:
            obs, r, term, trunc, info = env.step(4)  # remediate auto-target
            done = term or trunc
        m = info["episode_metrics"]
        csr.append(m["containment_success"])
        rewards.append(m["cumulative_reward"])
        nodes_max.append(m["nodes_compromised_max"])
    return {"csr": csr, "rewards": rewards, "nodes_max": nodes_max}


if __name__ == "__main__":
    t0 = time.time()
    print("=" * 70)
    print("CYBERWARENV SMOKE TEST")
    print("=" * 70)

    topo = build_topology("corporate", 100)
    print(f"[topology/corporate] {topo.summary()['num_nodes']} nodes, "
          f"{topo.summary()['num_edges']} edges, critical={topo.summary()['critical_nodes']}, "
          f"entry={topo.summary()['entry_nodes']}")
    topo2 = build_topology("datacenter", 100)
    print(f"[topology/datacenter] {topo2.summary()['num_nodes']} nodes, "
          f"{topo2.summary()['num_edges']} edges, critical={topo2.summary()['critical_nodes']}")

    for scenario, attacker in [("corporate", "scripted"), ("datacenter", "adaptive")]:
        for policy_name, runner in [("random", run_random_rollout), ("heuristic", run_heuristic_rollout)]:
            res = runner(scenario, attacker, seed=1, episodes=30)
            d = descriptive(res["csr"])
            ci = bootstrap_ci(res["csr"], n_resamples=2000)
            print(f"[{scenario}/{attacker}/{policy_name}] CSR={d['mean']:.3f} "
                  f"CI95=[{ci['ci_low']:.3f},{ci['ci_high']:.3f}] "
                  f"nodes_max={np.mean(res['nodes_max']):.1f} "
                  f"reward={np.mean(res['rewards']):.1f}")

    # speed test
    env = CyberWarEnv("corporate", "scripted")
    obs, _ = env.reset(seed=0)
    n = 20000
    t1 = time.time()
    for i in range(n):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        if term or trunc:
            env.reset(seed=i)
    dt = time.time() - t1
    print(f"[speed] {n/dt:,.0f} steps/sec -> 100k steps ≈ {100000/(n/dt):.0f}s per run")
    print(f"[total time] {time.time()-t0:.1f}s")
    print("ALL CHECKS PASSED")
