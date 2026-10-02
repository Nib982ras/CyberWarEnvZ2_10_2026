"""Sensor / observation model (Partial Observability, master prompt §12).

Each sensor produces probabilistic detections with false positives /
false negatives. Three reference configurations (A/B/C) allow studying
Sensor Distribution Shift.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

SENSOR_CONFIGS: Dict[str, Dict] = {
    "A": {"p_detect": 0.40, "p_fp": 0.05, "latency": 0},      # balanced IDS
    "B": {"p_detect": 0.55, "p_fp": 0.10, "latency": 0},      # high coverage, noisy
    "C": {"p_detect": 0.25, "p_fp": 0.02, "latency": 1},      # low-noise, low recall
}


class SensorSuite:
    """Generates the defender's alert vector each step."""

    def __init__(self, num_nodes: int, config: str = "A", rng: np.random.Generator = None):
        self.num_nodes = num_nodes
        cfg = SENSOR_CONFIGS[config]
        self.p_detect = cfg["p_detect"]
        self.p_fp = cfg["p_fp"]
        self.latency = cfg["latency"]
        self.rng = rng or np.random.default_rng()
        self._pending: list = []      # delayed alerts queue (latency > 0)

    def reset(self) -> None:
        self._pending = []

    def observe(self, compromised: np.ndarray, monitor_boost: bool) -> np.ndarray:
        """Return boolean alert vector [N] (True = alert on node)."""
        det_p = min(0.95, self.p_detect * (1.6 if monitor_boost else 1.0))
        fp_p = self.p_fp * (2.0 if monitor_boost else 1.0)

        true_hits = compromised & (self.rng.random(self.num_nodes) < det_p)
        false_hits = (~compromised) & (self.rng.random(self.num_nodes) < fp_p)
        alerts = true_hits | false_hits

        if self.latency > 0:
            # delayed delivery of true detections
            delivered = np.zeros(self.num_nodes, dtype=bool)
            for vec in self._pending:
                delivered |= vec
            self._pending.append(true_hits)
            while len(self._pending) > self.latency:
                self._pending.pop(0)
            return (alerts & ~true_hits) | delivered
        return alerts
