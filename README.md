# CyberWarEnv — Defensive Research & Simulation Environment

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23103285.svg)](https://doi.org/10.5281/zenodo.23103285)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.1.0-green.svg)](https://github.com/Nib982ras/CyberWarEnvZ2_10_2026/releases/tag/v2.1.0)

A Gymnasium-compatible **defensive** cyber-defense simulation environment for studying how
Deep Reinforcement Learning (DRL) defenders learn containment policies under partial
observability, sensor noise, and adaptive abstract attackers.

> **Companion code** for the manuscript *"Autonomous Cyber Defense in a Calibrated
> Simulation Environment: An Empirical Evaluation of PPO and DQN"* (Nibras Raad,
> Ahmed Chalak Shakir, Taha Mohammed Hasan — submitted to *Expert Systems with
> Applications*, Elsevier).

## Ethics / scope

This is a **defensive research simulator only**. It contains:
- ✗ no exploit code
- ✗ no real attack tooling
- ✗ no operational intrusion instructions
- ✓ abstract probabilistic attackers over abstract actions

The purpose is to study defender learning, not to build offensive capability.

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
├── cyberwarenv_scripts/    Environment tooling
│   ├── quick_test.py       Smoke test
│   ├── calibrate.py        12-cell difficulty calibration sweep
│   ├── verify_full.py      Train + evaluate one cell
│   ├── analyze.py          Aggregate per-run statistics
│   ├── figures.py          Generate publication figures
│   └── build_report.py     HTML report builder
├── paper_scripts/          Paper artifact chain (v2.1.0)
│   ├── extend_runs.py              Original n=10 extension worker
│   ├── extend_to_n20.py            n=10 → n=20 extension (fixed run_id collision)
│   ├── fix_corp_scripted.py         Re-runs corp/scripted in EXP-2026-000009/000010
│   ├── paper_analysis.py            Full statistical battery (Wilcoxon, Hedges' g, Holm, Mann-Whitney)
│   ├── paper_figures.py             Three publication figures
│   ├── fix_manifests.py             Manifest sync after RESUME
│   ├── verify_paper_provenance.py   Reverse-match shipped JSON against on-disk runs
│   ├── verify_registry_integrity.py SHA-256 hash verification of all 160 runs
│   └── build_manifest.py            Bilingual file manifest builder
├── README.md               This file
├── CHANGELOG.md            Version history
├── LICENSE                 MIT license
├── requirements.txt        Pinned Python dependencies
└── ENVIRONMENT.md          Exact software stack (recorded per experiment)
```

## Installation

```bash
git clone https://github.com/Nib982ras/CyberWarEnvZ2_10_2026.git
cd CyberWarEnvZ2_10_2026
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.12+ is recommended. See `ENVIRONMENT.md` for the exact stack used in the paper.

## Quickstart

```python
from cyberwarenv import CyberWarEnv, DifficultyProfile

env = CyberWarEnv(
    scenario="corporate",          # or "datacenter"
    attacker_kind="scripted",      # or "probabilistic", "adaptive"
    difficulty=DifficultyProfile(),  # calibrated operating point
    topology_seed=100,             # the seed used in all paper experiments
    env_seed=0,
)

obs, info = env.reset(seed=0)
done = False
while not done:
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated
print(f"Containment success: {info['episode_metrics']['containment_success']}")
env.close()
```

## Reproducing the paper

The full 160-run factorial study and every inferential number in the manuscript can
be regenerated from this repository plus the released dataset registry:

```bash
# 1. Smoke test the environment
python3 cyberwarenv_scripts/quick_test.py

# 2. Run the 12-cell calibration sweep (~5 minutes)
python3 cyberwarenv_scripts/calibrate.py

# 3. Train all 160 runs (~5 hours on one CPU thread)
python3 paper_scripts/extend_runs.py --worker dqn
python3 paper_scripts/extend_runs.py --worker ppo
python3 paper_scripts/extend_to_n20.py
python3 paper_scripts/fix_corp_scripted.py

# 4. Generate statistics + figures from the registry
python3 paper_scripts/paper_analysis.py
python3 paper_scripts/paper_figures.py

# 5. Verify all 320 SHA-256 hashes (160 config + 160 results)
python3 paper_scripts/verify_registry_integrity.py
# Expected output: "REGISTRY ARTIFACT INTEGRITY: PASS"
```

Alternatively, download the 160-run dataset registry from Zenodo
([DOI 10.5281/zenodo.23103285](https://doi.org/10.5281/zenodo.23103285), ~197 MB)
and skip step 3 — `paper_analysis.py` and `paper_figures.py` regenerate every
table and figure in the manuscript byte-identically from the released registry alone.

## Key results (v2.1.0, n=20 seeds per cell)

| Cell                    | PPO    | DQN    | Δ      | Holm p     | Hedges' g |
|-------------------------|--------|--------|--------|------------|-----------|
| Corporate / Scripted    | 0.912  | 0.710  | +0.202 | 6.5×10⁻⁴  | 1.64      |
| Corporate / Adaptive    | 0.912  | 0.747  | +0.165 | 1.0×10⁻³  | 1.03      |
| DataCenter / Scripted   | 0.837  | 0.555  | +0.282 | 1.5×10⁻⁵  | 2.26      |
| DataCenter / Adaptive   | 0.821  | 0.486  | +0.335 | 1.7×10⁻⁵  | 2.54      |

**Pooled exact Wilcoxon** over 79 seed-paired differences: PPO wins 73, DQN wins 6,
1 tie, **p < 10⁻¹⁵**, Hedges' g = 1.59.

PPO attains a higher containment success rate than DQN in every cell, with large
effect sizes (Cohen's convention: g ≥ 0.8 is "large").

## Releases

### v2.1.0 — 2026-10-03

- Extended the factorial registry from **n=10 to n=20** seeds per (cell, algorithm)
  condition (**160 total runs** across 10 experiment directories).
- Added `EXP-2026-000009` (corporate/scripted/DQN seeds 10–19) and
  `EXP-2026-000010` (corporate/scripted/PPO seeds 10–19) to avoid `run_id` collisions
  in the shared `EXP-2026-000007`/`000008` directories.
- All **320 SHA-256 hashes** (160 config + 160 results) verified as PASS by
  `paper_scripts/verify_registry_integrity.py`.
- `paper_analysis.py` and `paper_figures.py` regenerate every table and figure in the
  manuscript byte-identically from the extended registry.
- Statistical conclusions strengthened: all four per-cell Wilcoxon tests now significant
  at Holm-corrected p ≤ 1.1×10⁻³ (was p ≤ 0.018 at n=10); pooled exact test at
  p < 10⁻¹⁵ (was 1.9×10⁻⁹).

### v2.0.0 — 2026-10-02

- Initial public release.
- Gymnasium-compatible CyberWarEnv environment, 80-run factorial registry
  (EXP-2026-000001 through EXP-2026-000008), pre-registered difficulty calibration,
  exact statistical battery, three publication figures, full SHA-256 provenance chain.

## Citation

If you use CyberWarEnv in your research, please cite:

```bibtex
@misc{cyberwarenv2026,
  author       = {Raad, Nibras and Shakir, Ahmed Chalak and Hasan, Taha Mohammed},
  title        = {CyberWarEnv: Defensive Cyber Defense Simulation Environment},
  year         = {2026},
  version      = {2.1.0},
  publisher    = {GitHub},
  url          = {https://github.com/Nib982ras/CyberWarEnvZ2_10_2026},
  doi          = {10.5281/zenodo.23103285}
}
```

## License

- **Code:** MIT License — see [LICENSE](LICENSE)
- **Dataset:** CC-BY 4.0 — see [Zenodo record](https://doi.org/10.5281/zenodo.23103285)

## Contact

**Nibras Raad** (corresponding author)  
College of Science, University of Kirkuk, Kirkuk, Iraq  
ORCID: [0009-0005-4661-8820](https://orcid.org/0009-0005-4661-8820)  
Email: nibras98246@gmail.com

**Ahmed Chalak Shakir**  
Department of Network, College of Computer Science and Information Technology,
University of Kirkuk, Kirkuk, Iraq  
ORCID: [0000-0002-0862-3662](https://orcid.org/0000-0002-0862-3662)  
Email: ahmedchalak@uokirkuk.edu.iq

**Taha Mohammed Hasan**  
College of Science, University of Diyala, Baquba, Iraq  
ORCID: [0000-0002-4464-4655](https://orcid.org/0000-0002-4464-4655)  
Email: dr.tahamh@sciences.uodiyala.iq

## Acknowledgements

This research did not receive any specific grant from funding agencies in the public,
commercial, or not-for-profit sectors.
