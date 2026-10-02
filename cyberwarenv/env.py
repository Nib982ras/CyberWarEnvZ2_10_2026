"""CyberWarEnv Gymnasium environment (single-defender POMG view).

Formulation: Partially Observable Markov Game (POMG). The defender agent
observes sensor alerts (partial, noisy) and issues one defensive action
per step against an abstract simulated attacker.

Action space: Discrete(num_actions) — 9 defensive response types with
suspicion-based auto-targeting (SOC triage abstraction): each response
applies to the currently most-suspicious node (highest alert-EMA /
recent-alert / criticality). This mirrors the master prompt's action
list (§14: Monitor, Isolate, Contain, Remediate, Patch, ...) where
defensive actions are response types rather than (type, target) pairs,
and keeps the strategic decision — WHICH type of response — with the
agent.

Episode termination:
  - Defender WIN  : attacker foothold eliminated (containment success)
  - Attacker WIN  : exfiltration completed on a critical asset
  - Timeout       : episode budget exhausted (counts as not-contained)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .topology import NetworkTopology, build_topology, ZONE_IDS, NUM_ZONES
from .attack import AbstractAttacker, make_attacker
from .sensors import SensorSuite
from . import ENV_VERSION

ACTION_NAMES = [
    "monitor",              # 0 passive
    "increase_monitoring",  # 1 boost sensors 5 steps
    "isolate",              # 2 block node (pauses exfil, cuts spread)
    "contain",              # 3 isolate + high-prob clean
    "remediate",            # 4 clean attempt
    "patch",                # 5 harden node
    "restrict",             # 6 probabilistically cut node edges
    "deploy_decoy",         # 7 make node attractive honeypot
    "wait",                 # 8 passive
]
NUM_ACTIONS = len(ACTION_NAMES)
GLOBAL_ACTIONS = {0, 1, 8}


@dataclass
class DifficultyProfile:
    """Calibrated difficulty knobs (Research Calibration Profile)."""
    # attacker
    attack_frequency: float = 0.55        # P(attacker acts per step)
    attack_success_base: float = 0.72     # P(spread attempt succeeds on soft node)
    entry_success_scale: float = 0.90     # scale on initial foothold
    exfil_steps: int = 8                  # steps compromised on critical asset -> exfil
    p_persistence: float = 0.02
    evasion_factor: float = 0.60          # spread success multiplier under monitor boost
    adaptive_critical_weight: float = 4.0
    decoy_attract: float = 2.0            # decoy node spread success multiplier
    patch_effect: float = 0.45            # spread success multiplier on hardened node
    # defender mechanics
    contain_success: float = 0.85
    remediate_success: float = 0.70
    restrict_cut_prob: float = 0.60
    monitor_boost_steps: int = 5
    # reward shaping
    w_detection: float = 0.20
    w_false_positive: float = 0.10
    w_compromised: float = 1.00          # per compromised node per step
    w_op_impact: float = 0.40
    w_contain_bonus: float = 40.0
    w_exfil_penalty: float = 40.0
    w_timeout_penalty: float = 10.0
    # meta
    sensor_config: str = "A"
    max_steps: int = 60

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "DifficultyProfile":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CyberWarEnv(gym.Env):
    """Defensive cyber simulation environment for RL research."""

    metadata = {"render_modes": []}

    def __init__(self, scenario: str = "corporate", attacker_kind: str = "scripted",
                 difficulty: Optional[DifficultyProfile] = None,
                 topology_seed: int = 100, env_seed: int = 0):
        super().__init__()
        self.scenario = scenario
        self.attacker_kind = attacker_kind
        self.difficulty = difficulty or DifficultyProfile()
        self.topo_seed = topology_seed
        self.env_seed = env_seed

        # fixed topology per env instance (stable observation space)
        self.topo: NetworkTopology = build_topology(scenario, topology_seed)
        N = self.topo.num_nodes

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(12 * N + 3,), dtype=np.float32)
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        self._episode_rng = None
        self._reset_state()

    # ------------------------------------------------------------------
    def get_config(self) -> Dict:
        return {
            "env_version": ENV_VERSION,
            "scenario": self.scenario,
            "attacker_kind": self.attacker_kind,
            "topology_seed": self.topo_seed,
            "env_seed": self.env_seed,
            "topology_hash": self.topo.config_hash(),
            "topology": self.topo.summary(),
            "difficulty": self.difficulty.to_dict(),
            "num_actions": NUM_ACTIONS,
            "action_names": ACTION_NAMES,
        }

    # ------------------------------------------------------------------
    def _reset_state(self) -> None:
        self.rng = np.random.default_rng(self.env_seed)
        self.attacker: AbstractAttacker = make_attacker(
            self.attacker_kind, self.topo, self._attacker_diff(), self.rng)
        self.sensors = SensorSuite(self.topo.num_nodes, self.difficulty.sensor_config, self.rng)

        N = self.topo.num_nodes
        self.isolated = np.zeros(N, dtype=bool)
        self.hardened = np.zeros(N, dtype=bool)
        self.restricted_edges = self.topo.adjacency.copy()
        self.deployed_decoys = np.zeros(N, dtype=bool)
        self.monitor_boost = 0
        self.t = 0
        # belief-state memory: EMA of alert history per node (partial
        # observability — alerts flicker with p_detect < 1, so the agent
        # needs a memory trace of recent alerts)
        self.alert_ema = np.zeros(N, dtype=np.float32)
        self.alert_recent = np.zeros(N, dtype=bool)
        self.foothold_ever = bool(self.attacker.compromised.any())
        self.ep_metrics = {
            "containment_success": 0.0,
            "containment_time": float(self.difficulty.max_steps),
            "nodes_compromised_max": 0.0,
            "nodes_compromised_end": 0.0,
            "true_detections": 0.0,
            "compromise_exposures": 0.0,
            "false_positives": 0.0,
            "operational_impact": 0.0,
            "actions_used": 0.0,
            "cumulative_reward": 0.0,
        }

    def _attacker_diff(self) -> Dict:
        d = self.difficulty
        return {
            "attack_frequency": d.attack_frequency,
            "attack_success_base": d.attack_success_base,
            "entry_success_scale": d.entry_success_scale,
            "exfil_steps": d.exfil_steps,
            "persistence": d.p_persistence,
            "evasion": True,
            "evasion_factor": d.evasion_factor,
            "adaptive_critical_weight": d.adaptive_critical_weight,
            "decoy_attract": d.decoy_attract,
            "patch_effect": d.patch_effect,
        }

    # ------------------------------------------------------------------
    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.env_seed = seed
        self._reset_state()
        self.attacker.reset()
        self.sensors.reset()
        self.foothold_ever = bool(self.attacker.compromised.any())
        alerts = self.sensors.observe(self.attacker.compromised, False)
        self._update_alert_state(alerts)
        return self._get_obs(alerts), {"alerts": alerts.copy()}

    # ------------------------------------------------------------------
    def _update_alert_state(self, alerts: np.ndarray) -> None:
        self.alert_ema = 0.7 * self.alert_ema + 0.3 * alerts.astype(np.float32)
        self.alert_recent = self.alert_recent | alerts
        # "recent" decays: 20% chance per step to clear old flags
        decay = self.rng.random(len(alerts)) < 0.20
        self.alert_recent = self.alert_recent & ~decay

    def _get_obs(self, alerts: np.ndarray) -> np.ndarray:
        topo, N = self.topo, self.topo.num_nodes
        is_critical = np.zeros(N); is_critical[topo.critical_nodes] = 1.0
        is_decoy = np.zeros(N); is_decoy[topo.decoy_nodes] = 1.0
        is_decoy = is_decoy + self.deployed_decoys.astype(float)
        is_decoy = (is_decoy > 0).astype(float)
        is_server_like = ((topo.node_types == 0) | (topo.node_types == 3)).astype(float)
        zone_oh = np.zeros((N, NUM_ZONES))
        zone_oh[np.arange(N), topo.node_zones] = 1.0

        feats = np.concatenate([
            alerts.astype(np.float32)[:, None],          # 1 alert
            self.alert_ema[:, None],                     # 2 alert EMA (belief)
            self.alert_recent.astype(np.float32)[:, None],  # 3 recent alert
            is_server_like[:, None],                     # 4 server/critical
            is_critical[:, None],                        # 5 critical
            is_decoy[:, None],                           # 6 decoy
            self.isolated.astype(np.float32)[:, None],   # 7 isolated
            self.hardened.astype(np.float32)[:, None],   # 8 hardened
            zone_oh.astype(np.float32),                  # 9-12 zone one-hot
        ], axis=1).reshape(-1)

        glob = np.array([
            1.0 if self.monitor_boost > 0 else 0.0,
            self.t / max(1, self.difficulty.max_steps),
            alerts.sum() / N,
        ], dtype=np.float32)
        return np.concatenate([feats, glob]).astype(np.float32)

    # ------------------------------------------------------------------
    def _effective_adj(self) -> np.ndarray:
        return self.restricted_edges

    # ------------------------------------------------------------------
    def _auto_target(self) -> int:
        """SOC triage: the response applies to the most-suspicious node,
        scored ONLY from observable quantities (alerts, alert memory, node
        role). Deterministic tie-break by node index."""
        topo, N = self.topo, self.topo.num_nodes
        is_critical = np.zeros(N); is_critical[topo.critical_nodes] = 1.0
        is_server = (topo.node_types == 0).astype(float)
        score = (2.0 * self.alert_ema
                 + self.alert_recent.astype(float)
                 + 0.4 * is_critical
                 + 0.15 * is_server)
        if score.max() <= 0.0:
            # quiet network: fall back to the most valuable unprotected asset
            for c in topo.critical_nodes:
                if not self.hardened[c]:
                    return int(c)
            return int(topo.critical_nodes[0]) if len(topo.critical_nodes) else 0
        return int(np.argmax(score))

    def step(self, action: int):
        d = self.difficulty
        N = self.topo.num_nodes
        a_type = int(action)
        target = self._auto_target()
        assert self.action_space.contains(action)

        reward = 0.0
        terminated = False
        truncated = False

        # ---------------- defender action ----------------
        self.ep_metrics["actions_used"] += 0 if a_type in (0, 8) else 1.0
        if a_type == 1:
            self.monitor_boost = d.monitor_boost_steps
            reward -= 0.15
        elif a_type == 2:  # isolate
            if not self.isolated[target]:
                self.isolated[target] = True
                reward -= 0.20
                if not (self.attacker.compromised[target] or self.deployed_decoys[target]):
                    reward -= d.w_op_impact           # operational impact on benign node
                    self.ep_metrics["operational_impact"] += 1.0
                elif self.attacker.compromised[target]:
                    reward += 0.30                     # shaping: isolating real threat
        elif a_type == 3:  # contain
            reward -= 0.30
            if self.attacker.compromised[target] and self.rng.random() < d.contain_success:
                self.attacker.compromised[target] = False
                self.attacker.exfil_clock.pop(target, None)
                self.isolated[target] = True
                reward += 1.0
            elif not self.attacker.compromised[target]:
                reward -= d.w_op_impact
                self.ep_metrics["operational_impact"] += 1.0
            if self.alert_recent[target] or self.attacker.compromised[target]:
                reward += 0.25                         # shaping: targeted real suspicion
        elif a_type == 4:  # remediate
            reward -= 0.30
            if self.attacker.compromised[target] and self.rng.random() < d.remediate_success:
                self.attacker.compromised[target] = False
                self.attacker.exfil_clock.pop(target, None)
                reward += 1.0
            elif not self.attacker.compromised[target]:
                reward -= d.w_op_impact
                self.ep_metrics["operational_impact"] += 1.0
            if self.alert_recent[target] or self.attacker.compromised[target]:
                reward += 0.25                         # shaping: targeted real suspicion
            else:
                reward -= 0.15                         # shaping: wasted remediation
        elif a_type == 5:  # patch
            if not self.hardened[target]:
                self.hardened[target] = True
                reward -= 0.15
                if self.alert_recent[target] or self.topo.node_types[target] == 3:
                    reward += 0.15                     # shaping: patching suspect/critical
        elif a_type == 6:  # restrict communication
            edges = np.where(self.restricted_edges[target])[0]
            for e in edges:
                if self.rng.random() < d.restrict_cut_prob:
                    self.restricted_edges[target, e] = False
                    self.restricted_edges[e, target] = False
            reward -= 0.10
        elif a_type == 7:  # deploy decoy
            if not self.deployed_decoys[target]:
                self.deployed_decoys[target] = True
                reward -= 0.10

        # ---------------- attacker step ----------------
        topo_adj_backup = self.topo.adjacency
        self.topo.adjacency = self._effective_adj()
        # decoys attract adaptive attacker
        if a_type == 0 or a_type == 8:
            pass
        ev = self.attacker.step(self.t, self.isolated, self.hardened, self.monitor_boost > 0)
        self.topo.adjacency = topo_adj_backup
        if ev.get("acted"):
            self.foothold_ever = self.foothold_ever or bool(self.attacker.compromised.any())

        # ---------------- observation & detection ----------------
        if self.monitor_boost > 0:
            self.monitor_boost -= 1
        compromised = self.attacker.compromised
        alerts = self.sensors.observe(compromised, self.monitor_boost > 0)
        self._update_alert_state(alerts)

        true_det = (alerts & compromised).sum()
        fp = (alerts & ~compromised).sum()
        self.ep_metrics["true_detections"] += float(true_det)
        self.ep_metrics["compromise_exposures"] += float(compromised.sum())
        self.ep_metrics["false_positives"] += float(fp)
        reward += d.w_detection * true_det
        reward -= d.w_false_positive * fp
        reward -= d.w_compromised * compromised.sum()

        self.t += 1
        self.ep_metrics["nodes_compromised_max"] = max(
            self.ep_metrics["nodes_compromised_max"], float(compromised.sum()))

        # ---------------- termination ----------------
        if self.foothold_ever and not compromised.any():
            # attacker foothold fully eliminated -> containment success
            self.ep_metrics["containment_success"] = 1.0
            self.ep_metrics["containment_time"] = float(self.t)
            reward += d.w_contain_bonus
            terminated = True
        elif ev.get("exfil_complete"):
            reward -= d.w_exfil_penalty
            terminated = True
        elif self.t >= d.max_steps:
            truncated = True
            reward -= d.w_timeout_penalty

        self.ep_metrics["nodes_compromised_end"] = float(compromised.sum())
        self.ep_metrics["cumulative_reward"] += reward
        info = {
            "alerts": alerts.copy(),
            "attacker_event": ev,
            "containment_success": self.ep_metrics["containment_success"],
            "episode_metrics": dict(self.ep_metrics),
        }
        return self._get_obs(alerts), float(reward), terminated, truncated, info

    # ------------------------------------------------------------------
    def render(self):
        pass
