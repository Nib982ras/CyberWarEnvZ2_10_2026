#!/usr/bin/env python3
"""Extend the CyberWarEnv factorial study: add seeds 10-19 to every cell.

This produces the n=20 revision registry described in rebuttal_prep.pdf (Concern C1).
For each of the 8 (cell, algorithm) conditions, runs seeds 10-19 with the SAME:
  - calibrated operating points (from calibration_profile.json)
  - hyperparameters (SB3 defaults, fixed)
  - evaluation seed block (100 episodes, base seed 90_000)
  - SHA-256 manifest format (config_hash + artifact_hash)

Idempotent: skips any (cell, seed) whose results.json already says COMPLETE.

Output: new run folders under the existing EXP-2026-* directories, named
run_011 through run_020, matching the existing run_001..run_010 convention.

Compute budget: 8 cells x 10 seeds = 80 new runs, ~2-5 min each on one CPU.
Total: ~4-7 CPU-hours.
"""
import argparse
import json
import sys
import time

sys.path.insert(0, "/home/z/my-project")

import numpy as np
import torch
from stable_baselines3 import DQN, PPO

from cyberwarenv import CyberWarEnv, DifficultyProfile, ExperimentTracker

ROOT = "/home/z/my-project"
RUNS = f"{ROOT}/cyberwarenv_runs"
TRAIN_STEPS = 100_000
EVAL_EPISODES = 100
TOPO_SEED = {"corporate": 100, "datacenter": 200}

with open(f"{RUNS}/calibration_profile.json", encoding="utf-8") as f:
    CAL = json.load(f)
DIFF_S2 = DifficultyProfile(attack_frequency=CAL["stage2_corporate"]["attack_frequency"],
                            attack_success_base=CAL["stage2_corporate"]["attack_success_base"])
DIFF_S4 = DifficultyProfile.from_dict(CAL["stage4_datacenter"])

HP = {
    "DQN": {"learning_rate": 5e-4, "buffer_size": 150000, "batch_size": 256,
            "train_freq": 4, "gradient_steps": 1, "target_update_interval": 2000,
            "exploration_fraction": 0.25, "exploration_final_eps": 0.10,
            "learning_starts": 1000, "net_arch": [256, 256]},
    "PPO": {"n_steps": 1024, "batch_size": 256, "lr_schedule": "linear(3e-4->0)",
            "clip_range": "0.2->0.1 linear", "target_kl": 0.03, "gamma": 0.99,
            "ent_coef": 0.005, "n_epochs": 3, "net_arch": [256, 256]},
}

# Extension jobs: seeds 10-19 for each of the 8 (cell, algorithm) conditions.
# Maps each condition to the experiment directory that already holds seeds 0-9.
JOBS = [
    # corporate/scripted  -> EXP-2026-000007 (DQN seeds 5-9 already there) & EXP-2026-000008 (PPO seeds 5-9)
    {"scenario": "corporate", "attacker": "scripted", "algorithm": "DQN",
     "difficulty": DIFF_S2, "exp": "EXP-2026-000007", "seeds": list(range(10, 20))},
    {"scenario": "corporate", "attacker": "scripted", "algorithm": "PPO",
     "difficulty": DIFF_S2, "exp": "EXP-2026-000008", "seeds": list(range(10, 20))},
    # corporate/adaptive -> EXP-2026-000003 (DQN) & EXP-2026-000004 (PPO)
    {"scenario": "corporate", "attacker": "adaptive", "algorithm": "DQN",
     "difficulty": DIFF_S2, "exp": "EXP-2026-000003", "seeds": list(range(10, 20))},
    {"scenario": "corporate", "attacker": "adaptive", "algorithm": "PPO",
     "difficulty": DIFF_S2, "exp": "EXP-2026-000004", "seeds": list(range(10, 20))},
    # datacenter/scripted -> EXP-2026-000005 (DQN) & EXP-2026-000006 (PPO)
    {"scenario": "datacenter", "attacker": "scripted", "algorithm": "DQN",
     "difficulty": DIFF_S4, "exp": "EXP-2026-000005", "seeds": list(range(10, 20))},
    {"scenario": "datacenter", "attacker": "scripted", "algorithm": "PPO",
     "difficulty": DIFF_S4, "exp": "EXP-2026-000006", "seeds": list(range(10, 20))},
    # datacenter/adaptive -> EXP-2026-000007 (DQN seeds 5-9 already) & EXP-2026-000008 (PPO seeds 5-9)
    {"scenario": "datacenter", "attacker": "adaptive", "algorithm": "DQN",
     "difficulty": DIFF_S4, "exp": "EXP-2026-000007", "seeds": list(range(10, 20))},
    {"scenario": "datacenter", "attacker": "adaptive", "algorithm": "PPO",
     "difficulty": DIFF_S4, "exp": "EXP-2026-000008", "seeds": list(range(10, 20))},
]


def make_env(cell, seed):
    return CyberWarEnv(cell["scenario"], cell["attacker"], cell["difficulty"],
                       topology_seed=TOPO_SEED[cell["scenario"]], env_seed=seed)


def evaluate(model, cell, episodes=EVAL_EPISODES, base_seed=90_000):
    env = make_env(cell, base_seed)
    csr, ctime, nodes_max, fp, op, rew = [], [], [], [], [], []
    for ep in range(episodes):
        obs, info = env.reset(seed=base_seed + ep)
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, r, term, trunc, info = env.step(int(action))
            done = term or trunc
        m = info["episode_metrics"]
        csr.append(m["containment_success"])
        ctime.append(m["containment_time"])
        nodes_max.append(m["nodes_compromised_max"])
        fp.append(m["false_positives"])
        op.append(m["operational_impact"])
        rew.append(m["cumulative_reward"])
    env.close()
    return {"csr": csr, "containment_time": ctime, "nodes_compromised_max": nodes_max,
            "false_positives": fp, "operational_impact": op, "reward": rew}


class CSRCallback:
    def __init__(self, cell, every=20_000):
        self.cell, self.every = cell, every
        self.steps, self.csr = [], []
        self._next = every

    def __call__(self, locals_dict):
        model = locals_dict["self"]
        t = locals_dict["num_timesteps"]
        if t >= self._next:
            self._next += self.every
            res = evaluate(model, self.cell, episodes=12, base_seed=55_000)
            self.steps.append(int(t))
            self.csr.append(float(np.mean(res["csr"])))


def already_done(job, seed):
    import glob
    for prev in sorted(glob.glob(f"{RUNS}/{job['exp']}/run_*/results.json")):
        try:
            with open(prev, encoding="utf-8") as pf:
                pd_ = json.load(pf)
            with open(prev.replace("results.json", "config.json"), encoding="utf-8") as cf:
                pc = json.load(cf)
            if (pc["algorithm"] == job["algorithm"] and pc["seed"] == seed
                    and pd_.get("status") == "COMPLETE"
                    and pc["env_config"].get("scenario") == job["scenario"]
                    and pc["env_config"].get("attacker") == job["attacker"]):
                return prev
        except Exception:
            continue
    return None


def run_one(job, seed):
    done = already_done(job, seed)
    if done:
        with open(done, encoding="utf-8") as pf:
            pd_ = json.load(pf)
        print(f"  [{job['algorithm']} s={seed}] RESUME {done} csr={pd_['eval_summary']['csr_mean']:.3f}", flush=True)
        return
    # Use a deterministic run_id: run_{seed+1:03d} so seeds 10-19 map to run_011..run_020
    # This prevents the tracker.new_run() counter-based assignment from overwriting
    # existing run folders.
    run_id = f"run_{seed+1:03d}"
    tracker = ExperimentTracker(root=RUNS, experiment_id=job["exp"])
    cell = job
    t0 = time.time()
    # Build the RunRecord manually (avoid tracker.new_run's len(runs)+1 logic)
    from cyberwarenv.tracking import RunRecord, ENV_VERSION
    import datetime as _dt
    env_cfg = cell["difficulty"].to_dict() | {
        "scenario": cell["scenario"], "attacker": cell["attacker"],
        "train_steps": TRAIN_STEPS,
        "topology_seed": TOPO_SEED[cell["scenario"]],
        "eval_episodes": EVAL_EPISODES,
    }
    cfg = {
        "experiment_id": job["exp"],
        "run_id": run_id,
        "algorithm": cell["algorithm"],
        "seed": seed,
        "env_config": env_cfg,
        "train_config": {"sb3_defaults": False, "device": "cpu", "policy": "MlpPolicy",
                         "hyperparams": HP[cell["algorithm"]]},
        "env_version": ENV_VERSION,
        "software_versions": tracker.software_versions(),
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    import hashlib as _h, json as _j
    cfg["config_hash"] = _h.sha256(
        _j.dumps({k: v for k, v in cfg.items() if k != "config_hash"},
                 sort_keys=True, default=str).encode()
    ).hexdigest()
    run_dir = tracker.exp_dir / run_id
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "config.json", "w", encoding="utf-8") as f:
        import json as _j2
        _j2.dump(cfg, f, indent=2, ensure_ascii=False)
    rec = RunRecord(cfg, run_dir)
    cb = CSRCallback(cell)
    env = make_env(cell, seed)
    common = dict(seed=seed, device="cpu", verbose=0,
                  policy_kwargs=dict(net_arch=[256, 256]))
    if cell["algorithm"] == "DQN":
        model = DQN("MlpPolicy", env, buffer_size=150_000, learning_rate=5e-4,
                    batch_size=256, train_freq=4, gradient_steps=1,
                    target_update_interval=2_000, exploration_fraction=0.25,
                    exploration_final_eps=0.10, learning_starts=1_000, **common)
    else:
        model = PPO("MlpPolicy", env, n_steps=1024, batch_size=256,
                    learning_rate=lambda progress: progress * 3e-4,
                    clip_range=lambda progress: 0.10 + 0.10 * progress,
                    target_kl=0.03, gamma=0.99, ent_coef=0.005, n_epochs=3, **common)

    from stable_baselines3.common.callbacks import BaseCallback

    class _CB(BaseCallback):
        def _on_step(self):
            cb({"self": self.model, "num_timesteps": self.num_timesteps})
            return True

    model.learn(total_timesteps=TRAIN_STEPS, callback=_CB(), progress_bar=False)
    res = evaluate(model, cell)

    def _wilson(values, z=1.96):
        n = len(values)
        p = float(np.mean(values))
        denom = 1 + z**2 / n
        centre = (p + z**2 / (2 * n)) / denom
        half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
        return [float(centre - half), float(centre + half)]

    rec.finalize({
        "status": "COMPLETE",
        "wall_seconds": round(time.time() - t0, 1),
        "eval": res,
        "eval_summary": {
            "csr_mean": float(np.mean(res["csr"])),
            "csr_wilson_ci": _wilson(res["csr"]),
            "containment_time_mean": float(np.mean(res["containment_time"])),
            "nodes_compromised_max_mean": float(np.mean(res["nodes_compromised_max"])),
            "false_positives_mean": float(np.mean(res["false_positives"])),
            "operational_impact_mean": float(np.mean(res["operational_impact"])),
        },
        "csr_curve": {"steps": cb.steps, "csr": cb.csr},
        "model_params": int(sum(p.numel() for p in model.policy.parameters())),
    })
    model.save(f"{rec.run_dir}/model")
    print(f"  [{cell['algorithm']} s={seed}] CSR={np.mean(res['csr']):.3f} "
          f"({time.time()-t0:.0f}s) hash={rec.artifact_hash[:12] if hasattr(rec,'artifact_hash') else ''}",
          flush=True)


def cleanup_partials(jobs):
    """Remove run dirs lacking results.json, ONLY in experiments of the selected jobs."""
    import glob as _g
    import shutil
    owned = sorted({j["exp"] for j in jobs})
    for exp in owned:
        for rd in _g.glob(f"{RUNS}/{exp}/run_*"):
            import os
            if not os.path.exists(f"{rd}/results.json"):
                # Only remove if it has seed >= 10 (don't touch the original 0-9 runs)
                try:
                    cf = json.load(open(f"{rd}/config.json"))
                    if cf.get("seed", 0) >= 10:
                        shutil.rmtree(rd, ignore_errors=True)
                        print(f"  [cleanup] removed partial seed>=10 {rd}", flush=True)
                except Exception:
                    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default=None,
                    help="comma-separated job indices to run (e.g. 0,1)")
    ap.add_argument("--budget", type=int, default=36000,
                    help="stop BEFORE starting a new run once elapsed exceeds this (seconds)")
    args = ap.parse_args()
    torch.set_num_threads(1)
    jobs = JOBS
    if args.only:
        idx = [int(x) for x in args.only.split(",")]
        jobs = [jobs[i] for i in idx]
    cleanup_partials(jobs)
    total = sum(len(j["seeds"]) for j in jobs)
    print(f"EXTENSION WORKER: {total} new runs queued (seeds 10-19 for 8 cells)", flush=True)
    print(f"budget: {args.budget}s", flush=True)
    t_start = time.time()
    done_n = 0
    for job in jobs:
        key = f"{job['scenario']}/{job['attacker']}/{job['algorithm']} -> {job['exp']}"
        print(f"\n>>> {key}", flush=True)
        for s in job["seeds"]:
            if time.time() - t_start > args.budget:
                print(f"  [budget] stopping cleanly at {done_n}/{total} tasks "
                      f"({time.time()-t_start:.0f}s)", flush=True)
                return
            run_one(job, s)
            done_n += 1
            print(f"  progress {done_n}/{total} elapsed {time.time()-t_start:.0f}s", flush=True)
    print(f"\nEXTENSION ALL DONE in {(time.time()-t_start)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
