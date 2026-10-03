#!/usr/bin/env python3
"""Fix manifest.json files to match the current config.json config_hash.

This handles runs where RESUME re-wrote config.json (with a new created_utc)
but did not update manifest.json. The artifact_hash (sha256 of results.json)
is also recomputed for safety.

Safe to re-run: idempotent.
"""
import glob
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj):
    payload = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fix_one(run_dir: Path):
    cfg_path = run_dir / "config.json"
    res_path = run_dir / "results.json"
    man_path = run_dir / "manifest.json"
    if not (cfg_path.exists() and res_path.exists() and man_path.exists()):
        return None
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    res = json.loads(res_path.read_text(encoding="utf-8"))
    man = json.loads(man_path.read_text(encoding="utf-8"))
    if res.get("status") != "COMPLETE":
        return ("skip-incomplete", str(run_dir))

    cfg_obj = {k: v for k, v in cfg.items() if k != "config_hash"}
    new_cfg_hash = sha256_obj(cfg_obj)
    new_art_hash = sha256_file(res_path)

    old_cfg = man.get("config_hash")
    old_art = man.get("artifact_hash")
    if new_cfg_hash == old_cfg and new_art_hash == old_art:
        return ("ok", str(run_dir))

    man["config_hash"] = new_cfg_hash
    man["artifact_hash"] = new_art_hash
    # keep these in sync with config (in case run_id/exp_id were renamed)
    for k in ("experiment_id", "run_id", "env_version", "algorithm", "seed"):
        if k in cfg:
            man[k] = cfg[k]
    man_path.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    return ("fixed", str(run_dir))


def main():
    runs = sorted(glob.glob("cyberwarenv_runs/EXP-2026-*/run_*"))
    fixed = ok = skipped = 0
    for r in runs:
        result = fix_one(Path(r))
        if result is None:
            continue
        status, path = result
        if status == "fixed":
            fixed += 1
            print(f"  FIXED: {path}")
        elif status == "ok":
            ok += 1
        else:
            skipped += 1
    print(f"\nSummary: {ok} ok, {fixed} fixed, {skipped} skipped")


if __name__ == "__main__":
    main()
