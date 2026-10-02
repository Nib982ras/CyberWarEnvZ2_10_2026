"""CyberWarEnv — Defensive Research & Simulation Environment.

A Gymnasium-compatible environment for studying Autonomous Cyber Defense
(ACD) with Deep Reinforcement Learning, following the methodological
framework of:

    "Autonomous Cyber Defense via Deep Reinforcement Learning:
     A Methodologically Grounded Framework for Adversarial Network
     Environments"

ETHICS / SCOPE
--------------
This package is a DEFENSIVE research simulator only. It contains no
exploit code, no real attack tooling, and no operational intrusion
instructions. Attackers are abstract probabilistic policies over
abstract actions (Reconnaissance, Access Attempt, ...). The purpose is
to study defender learning, not to build offensive capability.
"""

__version__ = "2.0.0"
ENV_VERSION = "ENV-CWE-2.0.0"

from .topology import NetworkTopology, build_topology, SCENARIOS
from .attack import AbstractAttacker, ScriptedAttacker, ProbabilisticAttacker, AdaptiveAttacker
from .sensors import SensorSuite, SENSOR_CONFIGS
from .env import CyberWarEnv, DifficultyProfile
from .tracking import ExperimentTracker, RunRecord
from .stats import (bootstrap_ci, wilcoxon_test, mann_whitney_test, cohens_d,
                    holm_bonferroni, descriptive, rank_biserial, verify_against_claim)

__all__ = [
    "NetworkTopology", "build_topology", "SCENARIOS",
    "AbstractAttacker", "ScriptedAttacker", "ProbabilisticAttacker", "AdaptiveAttacker",
    "SensorSuite", "SENSOR_CONFIGS",
    "CyberWarEnv", "DifficultyProfile",
    "ExperimentTracker", "RunRecord",
    "bootstrap_ci", "wilcoxon_test", "mann_whitney_test", "cohens_d", "holm_bonferroni",
    "__version__", "ENV_VERSION",
]
