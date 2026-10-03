# Exact Software Environment

All versions below are recorded inside every run's `config.json`
(`software_versions` field) — this file is a human-readable summary, the
run registry is the authoritative record.

## Common stack (all experiments)

| Component | Version |
|---|---|
| Python | 3.12.14 |
| numpy | 2.1.3 |
| scipy | 1.14.1 |
| stable-baselines3 | 2.9.0 |
| gymnasium | 1.3.0 |
| Platform | Linux x86_64 (Alibaba Cloud kernel 5.10.134) |

## Torch differs between the two experiment generations

| Registry slice | torch version | Notes |
|---|---|---|
| `EXP-2026-000001`, `EXP-2026-000002` | **2.14.0+cu130** | Original 20-run verification batch (CUDA build, ran on CPU only) |
| `EXP-2026-000003` … `EXP-2026-000010` | **2.14.1+cpu** | 140-run factorial extension (v2.1.0) used for the paper's primary analysis |
| (excluded generation) | 2.14.0+cpu | Interrupted pre-reset expansion session (2026-09-03), duplicate seeds — **absent from the released registry** and excluded by the paper scripts' deterministic selection protocol |

Both builds are numerically equivalent for these workloads; the difference is
recorded here for full transparency. The paper's primary statistical analysis
(`paper_scripts/paper_analysis.py`) pools all four cells from the complete
160-run registry; a sensitivity check restricted to the 2.14.1+cpu runs yields
the same qualitative conclusions (PPO > DQN in every cell, Holm-corrected).

## Reproducibility notes

- **Topology seed**: `100` for corporate, `200` for data center (fixed topology
  per environment instance, stable observation space).
- **Evaluation**: 100 fixed-seed episodes per run, evaluation seeds fixed and
  recorded in each run's `results.json` (base seed `90_000`, episodes
  `90_000 + ep` for `ep` in `range(100)`).
- **Training**: 100,000 environment steps per run, every hyperparameter recorded
  in `config.json`'s `train_config` field.
- **SHA-256 manifests**: every run directory carries a `manifest.json` with
  SHA-256 hashes of its config (canonical object hash) and results; the script
  `paper_scripts/verify_registry_integrity.py` re-verifies all 320 hashes
  (160 config + 160 results) — verified 2026-10-03: PASS.
- **Full verification chain (2026-10-03)**: `paper_analysis.py` regenerates
  `paper_analysis.json` byte-identical, and `paper_figures.py` regenerates all
  three figures byte-identical, from the released registry alone.

## How to install the exact stack

```bash
# CPU-only PyTorch (matches the v2.1.0 extension runs)
pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu

# Remaining scientific stack
pip install numpy==2.1.3 scipy==1.14.1 stable-baselines3==2.9.0 \
            gymnasium==1.3.0 pandas matplotlib
```

Any compatible recent versions (numpy ≥ 1.26, scipy ≥ 1.11, etc.) will produce
equivalent numerical results; the pins above are for byte-exact reproducibility
of the released registry.
