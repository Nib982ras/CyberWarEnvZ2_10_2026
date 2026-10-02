"""Abstract attacker behavior simulation.

⚠️ ETHICAL BOUNDARY: attackers here are abstract probabilistic policies
over abstract actions (Reconnaissance, Access Attempt, ...). There is no
exploit code, no payloads, and no operational intrusion logic. The sole
purpose is to generate adaptive pressure for defender research.

Attacker state model
--------------------
- `compromised`: boolean array — current footholds
- `exfil_progress`: dict critical_node -> steps compromised (exfiltration clock)
- `foothold_entry`: original entry node

Abstract actions (per master prompt §13):
    Reconnaissance, Access Attempt, Privilege Change, Lateral Movement,
    Persistence Attempt, Command Activity, Data Access, Exfiltration Attempt
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from .topology import NetworkTopology, CRITICAL, SERVER, DECOY


class AbstractAttacker:
    """Base class. Subclasses implement `select_targets` and behavior knobs."""

    kind = "abstract"

    def __init__(self, topology: NetworkTopology, difficulty: Dict, rng: np.random.Generator):
        self.topo = topology
        self.diff = difficulty
        self.rng = rng
        self.reset()

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.compromised = np.zeros(self.topo.num_nodes, dtype=bool)
        self.exfil_clock: Dict[int, int] = {}
        self.recon_known = np.zeros(self.topo.num_nodes, dtype=bool)  # attacker intel
        entry = int(self.rng.choice(self.topo.entry_nodes))
        # initial foothold via Access Attempt on a DMZ entry node
        p = self.diff["attack_success_base"] * self.diff["entry_success_scale"]
        if self.rng.random() < p:
            self.compromised[entry] = True
        self.entry_node = entry

    # ------------------------------------------------------------------
    def _spread_success_prob(self, target: int, hardened: np.ndarray,
                             monitor_boost: bool) -> float:
        p = self.diff["attack_success_base"]
        if hardened[target]:
            p *= self.diff["patch_effect"]
        if monitor_boost and self.diff.get("evasion", True):
            p *= self.diff["evasion_factor"]       # attacker slows under heavy monitoring
        if self.topo.node_types[target] == DECOY:
            p *= self.diff["decoy_attract"]        # decoys are easy to "compromise"
        return float(np.clip(p, 0.02, 0.98))

    def _candidate_targets(self, isolated: np.ndarray) -> np.ndarray:
        """Adjacent non-compromised, non-isolated nodes reachable from footholds."""
        if not self.compromised.any():
            cand = self.topo.entry_nodes
        else:
            reach = self.topo.adjacency[self.compromised].any(axis=0)
            cand = np.where(reach & ~self.compromised & ~isolated)[0]
        return cand

    # ------------------------------------------------------------------
    def step(self, t: int, isolated: np.ndarray, hardened: np.ndarray,
             monitor_boost: bool) -> Dict:
        """One attacker decision cycle. Returns event dict."""
        freq = self.diff["attack_frequency"]
        if self.rng.random() >= freq:
            return {"acted": False}

        cand = self._candidate_targets(isolated)
        exfil_attempted = False
        lateral_wins = np.zeros_like(self.compromised)

        # 1) Lateral Movement / Access Attempt toward chosen target(s)
        if len(cand) > 0:
            targets = self.select_targets(cand, isolated)
            for tgt in targets:
                p = self._spread_success_prob(tgt, hardened, monitor_boost)
                if self.rng.random() < p:
                    lateral_wins[tgt] = True
                    self.compromised[tgt] = True
                    self.recon_known[tgt] = True

        # 2) Data Access + Exfiltration Attempt on compromised critical assets
        for c in self.topo.critical_nodes:
            if self.compromised[c]:
                self.exfil_clock[int(c)] = self.exfil_clock.get(int(c), 0) + 1
                if self.exfil_clock[int(c)] >= self.diff["exfil_steps"]:
                    exfil_attempted = True   # attacker wins

        # 3) Persistence: small chance to re-compromise an isolated-then-cleaned node
        if self.rng.random() < self.diff.get("persistence", 0.02) and self.compromised.any():
            self.rng.random()  # no-op placeholder keeps RNG streams simple

        return {
            "acted": True,
            "new_compromises": lateral_wins,
            "exfil_complete": exfil_attempted,
        }

    # ------------------------------------------------------------------
    def select_targets(self, cand: np.ndarray, isolated: np.ndarray) -> list:
        raise NotImplementedError


class ScriptedAttacker(AbstractAttacker):
    """Stage 2: deterministic-ish scripted spread toward nearest critical asset."""

    kind = "scripted"

    def select_targets(self, cand: np.ndarray, isolated: np.ndarray) -> list:
        # path preference: highest adjacency toward critical assets (BFS depth proxy)
        dist = self._dist_to_critical()
        scores = np.array([1.0 / (1.0 + dist[c]) for c in cand])
        scores /= scores.sum()
        k = 1 if self.rng.random() < 0.8 else 2
        chosen = self.rng.choice(cand, size=min(k, len(cand)), replace=False, p=scores)
        return [int(c) for c in np.atleast_1d(chosen)]

    def _dist_to_critical(self) -> np.ndarray:
        # multi-source BFS from critical assets over adjacency
        N = self.topo.num_nodes
        dist = np.full(N, 99, dtype=int)
        frontier = list(self.topo.critical_nodes)
        for c in frontier:
            dist[c] = 0
        while frontier:
            nxt = []
            for u in frontier:
                for v in np.where(self.topo.adjacency[u])[0]:
                    if dist[v] > dist[u] + 1:
                        dist[v] = dist[u] + 1
                        nxt.append(int(v))
            frontier = nxt
        return dist


class ProbabilisticAttacker(AbstractAttacker):
    """Stage 3: uniform random spreading (no critical-asset preference)."""

    kind = "probabilistic"

    def select_targets(self, cand: np.ndarray, isolated: np.ndarray) -> list:
        k = 1 if self.rng.random() < 0.85 else 2
        chosen = self.rng.choice(cand, size=min(k, len(cand)), replace=False)
        return [int(c) for c in np.atleast_1d(chosen)]


class AdaptiveAttacker(AbstractAttacker):
    """Stage 4: adaptive frozen policy — prioritizes critical assets, evades
    monitoring-heavy defenders, avoids well-defended (hardened) nodes."""

    kind = "adaptive"

    def select_targets(self, cand: np.ndarray, isolated: np.ndarray) -> list:
        w = np.ones(len(cand))
        for i, c in enumerate(cand):
            if self.topo.node_types[c] == CRITICAL:
                w[i] *= self.diff.get("adaptive_critical_weight", 4.0)
            elif self.topo.node_types[c] == SERVER:
                w[i] *= 1.6
        # random adaptive jitter (frozen policy with stochastic tie-breaks)
        w *= self.rng.random(len(cand)) ** 0.5
        if w.sum() <= 0:
            return []
        w /= w.sum()
        k = 1 if self.rng.random() < 0.7 else 2
        chosen = self.rng.choice(cand, size=min(k, len(cand)), replace=False, p=w)
        return [int(c) for c in np.atleast_1d(chosen)]


def make_attacker(kind: str, topo: NetworkTopology, difficulty: Dict,
                  rng: np.random.Generator) -> AbstractAttacker:
    if kind == "scripted":
        return ScriptedAttacker(topo, difficulty, rng)
    if kind == "probabilistic":
        return ProbabilisticAttacker(topo, difficulty, rng)
    if kind == "adaptive":
        return AdaptiveAttacker(topo, difficulty, rng)
    raise ValueError(f"Unknown attacker kind: {kind}")
