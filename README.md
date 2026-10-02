# CyberWarEnv — Defensive Research & Simulation Environment

A Gymnasium-compatible **defensive** cyber simulation for studying how Deep
Reinforcement Learning defenders learn containment policies under partial
observability, sensor noise, and adaptive abstract attackers. Companion code
for the manuscript *"Autonomous Cyber Defense in a Calibrated Simulation
Environment: An Empirical Evaluation of PPO and DQN"* (Nibras Raad,
University of Kirkuk).

**Ethics / scope.** This is a defensive research simulator only. It contains
no exploit code, no real attack tooling, and no operational intrusion
instructions. Attackers are abstract probabilistic policies over abstract
actions. The purpose is to study defender learning, not to build offensive
capability.

## Repository layout

```
.
├── cyberwarenv/            Python package (the environment itself)
│   ├── topology.py         Corporate (18 nodes) / DataCenter (20 nodes) generators
│   ├── attack.py           Scripted / Probabilistic / Adaptive abstract attackers
│   ├── sensors.py          3 sensor configurations (A/B/C) with FP/FN noise
│   ├── env.py              Gymnasium env: 9 SOC-triage actions, auto-targeting, shaped reward
│   ├── tracking.py         SHA-256 provenance tracking (ExperimentTracker, RunRecord)
│   └── stats.py            Bootstrap CI, Wilcoxon, Mann-Whitney, Cohen's d, Holm-Bonferroni
├── cyberwarenv_scripts/    Environment tooling: quick_test, calibrate, analyze, figures, verify_full
├── paper_scripts/          Paper artifact chain (see "Reproduce the paper" below)
├── PACKAGE_README.md       Original package README (module documentation)
├── ENVIRONMENT.md          Exact software stack recorded per experiment generation
└── PUBLISH_TO_GITHUB.md    Step-by-step guide to publish this repository
```

## Installation

```bash
git clone https://github.com/<username>/CyberWarEnv.git
cd CyberWarEnv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.12 was used for all experiments (see `ENVIRONMENT.md`).

## Quickstart

```python
from cyberwarenv import CyberWarEnv, DifficultyProfile

env = CyberWarEnv(
    scenario="corporate",          # or "datacenter"
    attacker_kind="scripted",      # or "probabilistic", "adaptive"
    difficulty=DifficultyProfile(),  # calibrated operating point (0.55, 0.72)
    topology_seed=100,             # the seed used in all paper experiments
    env_seed=0,
)

obs, info = env.reset(seed=0)
done = False
while not done:
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
    done = terminated or truncated
print(info)
```

## Reproduce the paper

The full pipeline, in order (CPU-only; the 80 training runs take roughly
7 hours on 4 cores):

```bash
# 1. Run the factorial study (2 topologies x 2 attackers x 2 algorithms x 10 seeds)
python paper_scripts/extend_runs.py --help          # inspect options first

# 2. Compute every statistic reported in the paper
python paper_scripts/paper_analysis.py              # -> paper_analysis.json

# 3. Regenerate the three figures from the analysis
python paper_scripts/paper_figures.py
```

Every inferential statement in the manuscript (Holm-corrected exact Wilcoxon
tests, Hedges' g, rank-biserial, Wilson intervals, pooled global test) is
recomputed by `paper_analysis.py` from the run registry — no numbers are
hard-coded.

**Run registry (80 runs, model weights, per-run SHA-256 manifests):** the
registry is too large for git and ships separately as
`CyberWarEnv_Dataset_Registry.zip` (also archived on Zenodo — DOI to be
inserted here after publication).

## Key results (all recomputable)

PPO achieves a higher containment success rate than DQN in all four cells of
the 2×2×2 design (Holm-corrected exact Wilcoxon, p ≤ 0.018; Hedges' g
1.56–3.01; pooled exact test over 40 seed pairs, p < 2e-9). Difficulty was
calibrated before any learning through a published 12-point sweep scored
against random and heuristic reference defenders.

## Citation

```bibtex
@software{raad2026cyberwarenv,
  author  = {Raad, Nibras},
  title   = {CyberWarEnv: A Calibrated Defensive Cyber Simulation
             for Deep Reinforcement Learning Research},
  year    = {2026},
  version = {2.0.0},
  url     = {https://github.com/<username>/CyberWarEnv}
}
```

## License

MIT — see [LICENSE](LICENSE).
