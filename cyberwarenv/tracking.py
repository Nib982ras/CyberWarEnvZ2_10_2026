"""Experiment tracking with full provenance (master prompt §41-42).

Every run records: Experiment ID, Run ID, seed, configuration hash,
environment version, algorithm version, timestamps, raw results, and
SHA-256 artifact hashes — the full provenance chain required by the
Research Integrity Gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ENV_VERSION = "ENV-CWE-2.0.0"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_obj(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


class ExperimentTracker:
    """File-based experiment registry with provenance."""

    def __init__(self, root: str = "cyberwarenv_runs", experiment_id: Optional[str] = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        # auto-increment experiment id
        if experiment_id is None:
            existing = sorted(self.root.glob("EXP-*"))
            n = len(existing) + 1
            experiment_id = f"EXP-2026-{n:06d}"
        self.experiment_id = experiment_id
        self.exp_dir = self.root / experiment_id
        self.exp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def software_versions(self) -> Dict:
        import numpy, scipy
        try:
            import torch
            torch_v = torch.__version__
        except ImportError:
            torch_v = "unavailable"
        try:
            import stable_baselines3 as sb3
            sb3_v = sb3.__version__
        except ImportError:
            sb3_v = "unavailable"
        try:
            import gymnasium
            gym_v = gymnasium.__version__
        except ImportError:
            gym_v = "unavailable"
        return {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "torch": torch_v,
            "stable_baselines3": sb3_v,
            "gymnasium": gym_v,
            "platform": platform.platform(),
        }

    # ------------------------------------------------------------------
    def new_run(self, algorithm: str, seed: int, env_config: Dict,
                train_config: Dict) -> "RunRecord":
        runs = sorted(self.exp_dir.glob("run_*"))
        run_id = f"run_{len(runs)+1:03d}"
        cfg = {
            "experiment_id": self.experiment_id,
            "run_id": run_id,
            "algorithm": algorithm,
            "seed": seed,
            "env_config": env_config,
            "train_config": train_config,
            "env_version": ENV_VERSION,
            "software_versions": self.software_versions(),
            "created_utc": datetime.now(timezone.utc).isoformat(),
        }
        cfg["config_hash"] = _sha256_obj(cfg)
        run_dir = self.exp_dir / run_id
        run_dir.mkdir(exist_ok=True)
        with open(run_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return RunRecord(cfg, run_dir)


@dataclass
class RunRecord:
    config: Dict
    run_dir: Path

    # ------------------------------------------------------------------
    def log(self, key: str, value) -> None:
        with open(self.run_dir / f"{key}.json", "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)

    def finalize(self, results: Dict) -> str:
        results = dict(results)
        results["finished_utc"] = datetime.now(timezone.utc).isoformat()
        results["status"] = results.get("status", "COMPLETE")
        path = self.run_dir / "results.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        artifact_hash = _sha256_file(path)
        manifest = {
            "experiment_id": self.config["experiment_id"],
            "run_id": self.config["run_id"],
            "config_hash": self.config["config_hash"],
            "artifact_hash": artifact_hash,
            "env_version": self.config["env_version"],
            "algorithm": self.config["algorithm"],
            "seed": self.config["seed"],
        }
        with open(self.run_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return artifact_hash
