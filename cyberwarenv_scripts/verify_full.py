"""Full Verification Runner — paper legacy numbers vs measured results.

Runs the pre-registered verification matrix (100k training steps per run,
5 seeds per algorithm, deterministic evaluation of 100 episodes per run):

    corporate / scripted (Stage 2):   DQN x5, PPO x5   (claims: 82.6%, 85.1%)
    datacenter / adaptive (Stage 4):  DQN x5, PPO x5   (claim:  68.9% DQN)

Provenance: every run gets config.json + results.json + manifest.json
(SHA-256 artifact hash) under cyberwarenv_runs/EXP-*/.

Usage: verify_full.py --cells 0,2 --experiment-id EXP-2026-000001
"""
import argparse
import json
import sys
import time

sys.path.insert(0, "/home/z/my-project/cyberwarenv")

import numpy as np
import torch

from stable_baselines3 import DQN, PPO
from cyberwarenv import CyberWarEnv, DifficultyProfile, ExperimentTracker

ROOT = "/home/z/my-project"
RUNS = f"{ROOT}/cyberwarenv_runs"
TRAIN_STEPS = 100_000
EVAL_EPISODES = 100
SEEDS = [0, 1, 2, 3, 4]
N_NODES = {"corporate": 18, "datacenter": 20}
TOPO_SEED = {"corporate": 100, "datacenter": 200}

# ---------------------------------------------------------------- profiles
with open(f"{RUNS}/calibration_profile.json", encoding="utf-8") as f:
    CAL = json.load(f)

p2 = CAL["stage2_corporate"]
DIFF_S2 = DifficultyProfile(attack_frequency=p2["attack_frequency"],
                            attack_success_base=p2["attack_success_base"])
DIFF_S4 = DifficultyProfile.from_dict(CAL["stage4_datacenter"])

MATRIX = [
    {"scenario": "corporate", "attacker": "scripted", "algorithm": "DQN",
     "difficulty": DIFF_S2, "claim": 0.826},
    {"scenario": "corporate", "attacker": "scripted", "algorithm": "PPO",
     "difficulty": DIFF_S2, "claim": 0.851},
    {"scenario": "datacenter", "attacker": "adaptive", "algorithm": "DQN",
     "difficulty": DIFF_S4, "claim": 0.689},
    {"scenario": "datacenter", "attacker": "adaptive", "algorithm": "PPO",
     "difficulty": DIFF_S4, "claim": None},
]

# ---------------------------------------------------------------- helpers

def make_eval_env(cell, seed):
    return CyberWarEnv(cell["scenario"], cell["attacker"], cell["difficulty"],
                       topology_seed=TOPO_SEED[cell["scenario"]], env_seed=seed)


def evaluate(model, cell, episodes=EVAL_EPISODES, base_seed=90_000):
    """Deterministic evaluation. Returns episode-level metrics."""
    env = make_eval_env(cell, base_seed)
    N = env.topo.num_nodes
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
    """Eval CSR curve every `every` steps (12 episodes, fixed eval seeds)."""

    def __init__(self, cell, every=20_000):
        self.cell, self.every = cell, every
        self.steps, self.csr = [], []
        self._next = every

    def __call__(self, locals_dict):
        model = locals_dict["self"]
        num_timesteps = locals_dict["num_timesteps"]
        if num_timesteps >= self._next:
            self._next += self.every
            res = evaluate(model, self.cell, episodes=12, base_seed=55_000)
            self.steps.append(int(num_timesteps))
            self.csr.append(float(np.mean(res["csr"])))
            print(f"    [curve] step={num_timesteps:>7d} eval_CSR={self.csr[-1]:.3f}",
                  flush=True)


def train_one(cell, seed, tracker):
    t0 = time.time()
    # ---- idempotent resume: skip if this (algorithm, seed) already completed
    import glob as _glob
    for prev in sorted(_glob.glob(str(tracker.exp_dir / "run_*" / "results.json"))):
        try:
            with open(prev, encoding="utf-8") as pf:
                pd_ = json.load(pf)
            cfg_path = prev.replace("results.json", "config.json")
            with open(cfg_path, encoding="utf-8") as cf:
                pc = json.load(cf)
            if pc["algorithm"] == cell["algorithm"] and pc["seed"] == seed \
                    and pd_.get("status") == "COMPLETE" \
                    and pc["env_config"].get("scenario") == cell["scenario"]:
                print(f"  [{cell['algorithm']} seed={seed}] RESUMED from {prev}", flush=True)
                return {"seed": seed, "csr": pd_["eval_summary"]["csr_mean"],
                        "csr_episodes": pd_["eval"]["csr"],
                        "run_id": pc["run_id"],
                        "artifact_hash": pd_.get("artifact_hash", ""),
                        "containment_time": pd_["eval_summary"]["containment_time_mean"],
                        "nodes_max": pd_["eval_summary"]["nodes_compromised_max_mean"]}
        except Exception:
            continue
    rec = tracker.new_run(cell["algorithm"], seed, cell["difficulty"].to_dict()
                          | {"scenario": cell["scenario"],
                             "attacker": cell["attacker"],
                             "train_steps": TRAIN_STEPS,
                             "topology_seed": TOPO_SEED[cell["scenario"]],
                             "eval_episodes": EVAL_EPISODES},
                          {"sb3_defaults": False, "device": "cpu",
                           "policy": "MlpPolicy",
                           "hyperparams": HP[cell["algorithm"]]})
    cb = CSRCallback(cell)

    if cell["algorithm"] == "DQN":
        model = DQN("MlpPolicy", make_eval_env(cell, seed), seed=seed, device="cpu",
                    verbose=0, buffer_size=150_000, learning_rate=5e-4,
                    batch_size=256, train_freq=4, gradient_steps=1,
                    target_update_interval=2_000,
                    exploration_fraction=0.25, exploration_final_eps=0.10,
                    learning_starts=1_000,
                    policy_kwargs=dict(net_arch=[256, 256]))
    else:
        model = PPO("MlpPolicy", make_eval_env(cell, seed), seed=seed, device="cpu",
                    verbose=0, n_steps=1024, batch_size=256,
                    # linear decay + KL guard + small clip -> stable near-solved policy
                    learning_rate=lambda progress: progress * 3e-4,
                    clip_range=lambda progress: 0.10 + 0.10 * progress,
                    target_kl=0.03, gamma=0.99, ent_coef=0.005, n_epochs=3,
                    policy_kwargs=dict(net_arch=[256, 256]))

    # hook the CSR curve into the model's collect loop
    orig_collect = model.collect_rollouts if cell["algorithm"] == "PPO" else None

    if cell["algorithm"] == "PPO":
        from stable_baselines3.common.callbacks import BaseCallback

        class _CB(BaseCallback):
            def _on_step(self):
                d = {"self": self.model, "num_timesteps": self.num_timesteps}
                cb(d)
                return True

        model.learn(total_timesteps=TRAIN_STEPS, callback=_CB(), progress_bar=False)
    else:
        from stable_baselines3.common.callbacks import BaseCallback

        class _CB(BaseCallback):
            def _on_step(self):
                d = {"self": self.model, "num_timesteps": self.num_timesteps}
                cb(d)
                return True

        model.learn(total_timesteps=TRAIN_STEPS, callback=_CB(), progress_bar=False)

    res = evaluate(model, cell)
    artifact_hash = rec.finalize({
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
    print(f"  [{cell['algorithm']} seed={seed}] CSR={np.mean(res['csr']):.3f} "
          f"({time.time()-t0:.0f}s) hash={artifact_hash[:12]}", flush=True)
    return {"seed": seed, "csr": float(np.mean(res["csr"])),
            "csr_episodes": res["csr"], "run_id": rec.config["run_id"],
            "artifact_hash": artifact_hash,
            "containment_time": float(np.mean(res["containment_time"])),
            "nodes_max": float(np.mean(res["nodes_compromised_max"]))}


def _wilson(values, z=1.96):
    """Wilson score interval for a binomial proportion."""
    n = len(values)
    p = float(np.mean(values))
    if n == 0:
        return [0.0, 0.0]
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return [float(centre - half), float(centre + half)]


HP = {
    "DQN": {"learning_rate": 5e-4, "buffer_size": 150000, "batch_size": 256,
            "train_freq": 4, "gradient_steps": 1, "target_update_interval": 2000,
            "exploration_fraction": 0.25, "exploration_final_eps": 0.10,
            "learning_starts": 1000, "net_arch": [256, 256]},
    "PPO": {"n_steps": 1024, "batch_size": 256, "lr_schedule": "linear(3e-4->0)",
            "clip_range": "0.2->0.1 linear", "target_kl": 0.03, "gamma": 0.99,
            "ent_coef": 0.005, "n_epochs": 3, "net_arch": [256, 256]},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=str, default="0,1,2,3",
                    help="comma-separated indices into MATRIX")
    ap.add_argument("--seeds", type=str, default="0,1,2,3,4",
                    help="comma-separated seeds to run")
    ap.add_argument("--experiment-id", type=str, default=None)
    args = ap.parse_args()
    torch.set_num_threads(1)
    tracker = ExperimentTracker(root=RUNS, experiment_id=args.experiment_id)
    cell_idx = [int(x) for x in args.cells.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]
    print("=" * 78)
    print(f"FULL VERIFICATION — cells {cell_idx} seeds {seeds} x "
          f"{TRAIN_STEPS:,} steps | experiment {tracker.experiment_id}")
    print("=" * 78, flush=True)
    all_results = {}
    for ci in cell_idx:
        cell = MATRIX[ci]
        key = f"{cell['scenario']}/{cell['attacker']}/{cell['algorithm']}"
        print(f"\n>>> {key}  (claimed: {cell['claim']})", flush=True)
        runs = [train_one(cell, s, tracker) for s in seeds]
        all_results[key] = {"cell": {k: v for k, v in cell.items()
                                     if k != "difficulty"},
                            "difficulty": cell["difficulty"].to_dict(),
                            "runs": runs,
                            "claim": cell["claim"]}
        csrs = [r["csr"] for r in runs]
        print(f"    => {key}: CSR={np.mean(csrs):.3f} ± {np.std(csrs):.3f}")

    with open(f"{RUNS}/verification_results_{tracker.experiment_id}.json", "w", encoding="utf-8") as f:
        json.dump({"experiment_id": tracker.experiment_id,
                   "train_steps": TRAIN_STEPS,
                   "seeds": SEEDS,
                   "eval_episodes": EVAL_EPISODES,
                   "results": all_results}, f, indent=2, ensure_ascii=False)
    print(f"\n[saved] {RUNS}/verification_results_{tracker.experiment_id}.json")


if __name__ == "__main__":
    main()
