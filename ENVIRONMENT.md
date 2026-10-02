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
| EXP-2026-000001, EXP-2026-000002 | **2.14.0+cu130** | Original 20-run verification batch (CUDA build, ran on CPU only) |
| EXP-2026-000003 … EXP-2026-000008 | **2.14.1+cpu** | 60-run factorial extension used for the paper's primary analysis |
| (excluded generation) | 2.14.0+cpu | Interrupted pre-reset expansion session (2026-09-03), duplicate seeds — **absent from the released registry** and excluded by the paper scripts' deterministic selection protocol |

Both builds are numerically equivalent for these workloads; the difference is
recorded here for full transparency. The paper's primary statistical analysis
(`paper_scripts/paper_analysis.py`) pools all four cells from the complete
80-run registry; a sensitivity check restricted to the 2.14.1+cpu runs yields
the same qualitative conclusions (PPO > DQN in every cell, Holm-corrected).

## Reproducibility notes

- Topology seed: **100** for every run (fixed topology per environment
  instance, stable observation space).
- Evaluation: 100 fixed-seed episodes per run, evaluation seeds fixed and
  recorded in each run's `results.json`.
- Every run directory carries a `manifest.json` with SHA-256 hashes of its
  config (canonical object hash) and results; `paper_scripts/build_manifest.py`
  rebuilds the registry-level manifest, and `paper_scripts/verify_registry_integrity.py`
  re-verifies all 160 hashes (80 runs x config + results) — verified 2026-10-02: PASS.
- Full verification chain (2026-10-02): `paper_analysis.py` regenerates
  `paper_analysis.json` byte-identical, and `paper_figures.py` regenerates all
  three figures byte-identical, from the released registry alone.
