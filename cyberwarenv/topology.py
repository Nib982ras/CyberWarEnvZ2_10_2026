"""Network topology model and procedural generators.

Topologies are generated ONCE per environment instance and remain fixed
across resets (environment version stability). Topology randomization
for the Generalization Laboratory is done by creating new env instances
with different seeds, not by mutating mid-experiment.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

ZONE_IDS = {"DMZ": 0, "Corporate": 1, "DataCenter": 2, "Management": 3}
NUM_ZONES = len(ZONE_IDS)

# Node types
SERVER, CLIENT, SEC_DEVICE, CRITICAL, DECOY = 0, 1, 2, 3, 4


@dataclass
class NetworkTopology:
    """A fixed defensive network topology."""
    name: str
    num_nodes: int
    node_types: np.ndarray          # [N] int
    node_zones: np.ndarray          # [N] int
    adjacency: np.ndarray           # [N,N] bool
    critical_nodes: np.ndarray      # indices of critical assets
    decoy_nodes: np.ndarray         # indices of decoy assets
    entry_nodes: np.ndarray         # attacker entry candidates (DMZ)
    seed: int
    generator: str = "enterprise"

    # ------------------------------------------------------------------
    def summary(self) -> Dict:
        return {
            "name": self.name,
            "num_nodes": int(self.num_nodes),
            "num_edges": int(self.adjacency.sum() // 2),
            "zones": {z: int((self.node_zones == zi).sum()) for z, zi in ZONE_IDS.items()},
            "critical_nodes": [int(i) for i in self.critical_nodes],
            "decoy_nodes": [int(i) for i in self.decoy_nodes],
            "entry_nodes": [int(i) for i in self.entry_nodes],
            "seed": int(self.seed),
            "generator": self.generator,
        }

    def config_hash(self) -> str:
        payload = json.dumps(self.summary(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


def _zone_slice(nodes: List[dict], zone: str) -> List[int]:
    zi = ZONE_IDS[zone]
    return [n["idx"] for n in nodes if n["zone"] == zi]


def _build_adjacency(nodes: List[dict], rng: np.random.Generator,
                     intra_p: float, dmz_corp_p: float, corp_dc_p: float,
                     mgmt_all_p: float) -> np.ndarray:
    N = len(nodes)
    adj = np.zeros((N, N), dtype=bool)
    for i in range(N):
        for j in range(i + 1, N):
            zi, zj = nodes[i]["zone"], nodes[j]["zone"]
            p = 0.0
            if zi == zj:
                p = intra_p
            elif {zi, zj} == {ZONE_IDS["DMZ"], ZONE_IDS["Corporate"]}:
                p = dmz_corp_p
            elif {zi, zj} == {ZONE_IDS["Corporate"], ZONE_IDS["DataCenter"]}:
                p = corp_dc_p
            elif ZONE_IDS["Management"] in (zi, zj):
                p = mgmt_all_p
            if p > 0 and rng.random() < p:
                adj[i, j] = adj[j, i] = True
    # guarantee connectivity: chain every node to at least one earlier node
    for i in range(1, N):
        if not adj[i].any():
            j = int(rng.integers(0, i))
            adj[i, j] = adj[j, i] = True
    return adj


def _finish(name: str, nodes: List[dict], adj: np.ndarray, seed: int,
            generator: str, n_critical: int, n_decoys: int,
            rng: np.random.Generator) -> NetworkTopology:
    N = len(nodes)
    types = np.array([n["type"] for n in nodes], dtype=int)
    zones = np.array([n["zone"] for n in nodes], dtype=int)

    server_idx = [n["idx"] for n in nodes if n["type"] == SERVER]
    # critical assets: prefer servers in DataCenter then Corporate
    dc_servers = [i for i in server_idx if zones[i] == ZONE_IDS["DataCenter"]]
    corp_servers = [i for i in server_idx if zones[i] == ZONE_IDS["Corporate"]]
    critical: List[int] = []
    rng.shuffle(dc_servers)
    rng.shuffle(corp_servers)
    for pool in (dc_servers, corp_servers):
        while len(critical) < n_critical and pool:
            critical.append(pool.pop())
    if len(critical) < n_critical and server_idx:
        critical.append(int(rng.choice(server_idx)))
    types[critical] = CRITICAL

    decoys: List[int] = []
    clients = [n["idx"] for n in nodes if n["type"] == CLIENT]
    rng.shuffle(clients)
    decoys = clients[:n_decoys]
    types[decoys] = DECOY

    dmz = [i for i in range(N) if zones[i] == ZONE_IDS["DMZ"]]
    return NetworkTopology(
        name=name, num_nodes=N, node_types=types, node_zones=zones,
        adjacency=adj, critical_nodes=np.array(critical, dtype=int),
        decoy_nodes=np.array(decoys, dtype=int),
        entry_nodes=np.array(dmz, dtype=int), seed=seed, generator=generator,
    )


def build_topology(scenario: str, seed: int) -> NetworkTopology:
    """Build a scenario topology deterministically from a seed."""
    rng = np.random.default_rng(seed)
    if scenario == "corporate":
        # Enterprise-like: DMZ(3) Corporate(9) DataCenter(4) Management(2) = 18
        plan = [("DMZ", SEC_DEVICE, 1), ("DMZ", SERVER, 1), ("DMZ", CLIENT, 1),
                ("Corporate", SERVER, 3), ("Corporate", CLIENT, 5), ("Corporate", SEC_DEVICE, 1),
                ("DataCenter", SERVER, 3), ("DataCenter", CLIENT, 1),
                ("Management", SERVER, 1), ("Management", CLIENT, 1)]
        nodes = []
        idx = 0
        for zone, t, k in plan:
            for _ in range(k):
                nodes.append({"idx": idx, "zone": ZONE_IDS[zone], "type": t})
                idx += 1
        adj = _build_adjacency(nodes, rng, intra_p=0.45, dmz_corp_p=0.55,
                               corp_dc_p=0.4, mgmt_all_p=0.3)
        return _finish("corporate", nodes, adj, seed, "enterprise",
                       n_critical=2, n_decoys=2, rng=rng)

    elif scenario == "datacenter":
        # Denser, server-heavy: DMZ(2) Corporate(6) DataCenter(9) Management(3) = 20
        plan = [("DMZ", SEC_DEVICE, 1), ("DMZ", SERVER, 1),
                ("Corporate", SERVER, 2), ("Corporate", CLIENT, 3), ("Corporate", SEC_DEVICE, 1),
                ("DataCenter", SERVER, 8), ("DataCenter", CLIENT, 1),
                ("Management", SERVER, 2), ("Management", CLIENT, 1)]
        nodes = []
        idx = 0
        for zone, t, k in plan:
            for _ in range(k):
                nodes.append({"idx": idx, "zone": ZONE_IDS[zone], "type": t})
                idx += 1
        adj = _build_adjacency(nodes, rng, intra_p=0.55, dmz_corp_p=0.6,
                               corp_dc_p=0.5, mgmt_all_p=0.35)
        return _finish("datacenter", nodes, adj, seed, "datacenter",
                       n_critical=3, n_decoys=1, rng=rng)

    raise ValueError(f"Unknown scenario: {scenario}")


SCENARIOS = {
    "corporate": {
        "description": "Enterprise-like network, 18 nodes, 2 critical assets",
        "builder": "enterprise",
    },
    "datacenter": {
        "description": "Dense data-center network, 20 nodes, 3 critical assets",
        "builder": "datacenter",
    },
}
