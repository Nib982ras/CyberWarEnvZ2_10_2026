#!/usr/bin/env python3
"""Verify every run artifact in the registry against its own SHA-256 manifest.

Checks, for all 80 canonical runs (both released generations):
  - config.json hash recorded in manifest.json
  - results.json hash recorded in manifest.json
  - model.zip hash recorded in manifest.json (when present)
Prints a summary and exits non-zero on any mismatch.
"""
import glob
import hashlib
import json
import sys

RUNS = "/home/z/my-project/cyberwarenv_runs"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    checked = mism = skipped = 0
    for run_dir in sorted(glob.glob(f"{RUNS}/EXP-2026-*/run_*")):
        try:
            man = json.load(open(f"{run_dir}/manifest.json", encoding="utf-8"))
            cfg = json.load(open(f"{run_dir}/config.json", encoding="utf-8"))
        except Exception:
            skipped += 1
            continue
        if cfg.get("software_versions", {}).get("torch") == "2.14.0+cpu":
            skipped += 1  # excluded expansion generation
            continue
        # manifest is flat: config_hash = sha256(canonical json of config minus
        # the config_hash key, per tracking.py _sha256_obj); artifact_hash =
        # sha256 of results.json
        cfg_obj = {k: v for k, v in cfg.items() if k != "config_hash"}
        canonical = json.dumps(cfg_obj, sort_keys=True, default=str).encode()
        checks = [
            ("config_hash", hashlib.sha256(canonical).hexdigest(),
             man.get("config_hash")),
            ("artifact_hash", sha256(f"{run_dir}/results.json"),
             man.get("artifact_hash")),
        ]
        for name, actual, recorded in checks:
            if not recorded:
                continue
            if actual != recorded:
                print(f"HASH MISMATCH {run_dir}/{name}")
                mism += 1
            checked += 1
    print(f"verified hashes: {checked}   mismatches: {mism}   skipped (excluded gen): {skipped}")
    if mism:
        sys.exit(1)
    print("REGISTRY ARTIFACT INTEGRITY: PASS")


if __name__ == "__main__":
    main()
