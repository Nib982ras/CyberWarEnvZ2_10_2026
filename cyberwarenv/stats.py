"""Statistical Analysis Engine (master prompt §27-28).

Non-parametric tests, bootstrap confidence intervals, effect sizes, and
multiple-comparison correction. Test selection follows the master
prompt's rule: choose by research design / data type / pairing /
distribution / sample size — never by desired p-value.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np
from scipy import stats


def bootstrap_ci(values: Sequence[float], stat=np.mean, n_resamples: int = 10000,
                 confidence: float = 0.95, seed: int = 0) -> Dict:
    """Bootstrap CI for an arbitrary statistic (default: mean)."""
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    if len(x) == 0:
        return {"stat": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
                "n": 0}
    boots = np.empty(n_resamples)
    for i in range(n_resamples):
        boots[i] = stat(x[rng.integers(0, len(x), len(x))])
    alpha = (1 - confidence) / 2
    lo, hi = np.quantile(boots, [alpha, 1 - alpha])
    return {"stat": float(stat(x)), "ci_low": float(lo), "ci_high": float(hi),
            "n": int(len(x)), "n_resamples": n_resamples, "confidence": confidence}


def wilcoxon_test(a: Sequence[float], b: Sequence[float]) -> Dict:
    """Wilcoxon signed-rank test for paired samples."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = min(len(a), len(b))
    if n < 5:
        return {"test": "wilcoxon", "skipped": "insufficient paired samples", "n": int(n)}
    stat, p = stats.wilcoxon(a[:n], b[:n])
    return {"test": "wilcoxon", "statistic": float(stat), "p_value": float(p), "n": int(n)}


def mann_whitney_test(a: Sequence[float], b: Sequence[float]) -> Dict:
    """Mann–Whitney U for independent samples (two-sided)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or len(b) < 3:
        return {"test": "mann_whitney", "skipped": "insufficient samples",
                "n_a": len(a), "n_b": len(b)}
    stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {"test": "mann_whitney", "statistic": float(stat), "p_value": float(p),
            "n_a": int(len(a)), "n_b": int(len(b))}


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Cohen's d (pooled SD) for two independent samples."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    pooled = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled)


def rank_biserial(a: Sequence[float], b: Sequence[float]) -> float:
    """Rank-biserial correlation for Mann–Whitney."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or len(b) < 3:
        return float("nan")
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return float(2 * u / (len(a) * len(b)) - 1)


def holm_bonferroni(p_values: Sequence[float], alpha: float = 0.05) -> Dict:
    """Holm–Bonferroni step-down correction."""
    p = np.asarray(p_values, float)
    m = len(p)
    order = np.argsort(p)
    reject = np.zeros(m, dtype=bool)
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = (m - rank) * p[idx]
        running_max = max(running_max, adj)
        reject[idx] = running_max < alpha
    adjusted = np.minimum.accumulate(
        (p[order] * (m - np.arange(m)))[::-1])[::-1] if m else p
    adj_full = np.empty(m)
    adj_full[order] = np.clip(adjusted, 0, 1)
    return {"adjusted_p": adj_full.tolist(), "reject_null": reject.tolist(), "alpha": alpha}


def descriptive(values: Sequence[float]) -> Dict:
    x = np.asarray(values, float)
    if len(x) == 0:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "mean": float(x.mean()),
        "median": float(np.median(x)),
        "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
        "iqr": float(np.subtract(*np.percentile(x, [75, 25]))),
        "min": float(x.min()),
        "max": float(x.max()),
    }


def verify_against_claim(measured_cis: List[Dict], claimed: float) -> Dict:
    """Compare measured bootstrap CI against a legacy claimed value.

    Status:
      VERIFIED   — claimed value inside the 95% CI
      ABOVE      — measured significantly above the claim (env easier / different)
      BELOW      — measured significantly below the claim
    """
    if not measured_cis:
        return {"status": "UNVERIFIED", "reason": "no measured data"}
    lo = min(c["ci_low"] for c in measured_cis)
    hi = max(c["ci_high"] for c in measured_cis)
    stat = float(np.mean([c["stat"] for c in measured_cis]))
    if lo <= claimed <= hi:
        status = "VERIFIED"
    elif stat > claimed:
        status = "ABOVE_CLAIM"
    else:
        status = "BELOW_CLAIM"
    return {"status": status, "claimed": claimed, "measured_mean": stat,
            "ci_pooled_low": float(lo), "ci_pooled_high": float(hi)}
