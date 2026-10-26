"""Road graph with optional fixed-time signals at intersections."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class Signal:
    """Two-phase fixed-time plan: north-south green, then east-west green,
    then an all-red remainder. Times are seconds."""

    cycle_s: float
    ns_green_s: float
    ew_green_s: float
    offset_s: float = 0.0  # epoch-relative start of a cycle (modeled)

    def __post_init__(self) -> None:
        if self.cycle_s <= 0:
            raise ValueError("cycle_s must be positive")
        if self.ns_green_s <= 0 or self.ew_green_s <= 0:
            raise ValueError("green times must be positive")
        if self.ns_green_s + self.ew_green_s > self.cycle_s:
            raise ValueError("green times exceed the cycle length")


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    length_m: float
    speed_kmh: float
    axis: str  # approach axis at the target: "NS" or "EW"

    @property
    def base_time_s(self) -> float:
        return self.length_m / (self.speed_kmh / 3.6)


@dataclass(frozen=True)
class Node:
    id: str
    lat: float
    lon: float
    signal: Signal | None = None


class Graph:
    def __init__(self, nodes: dict[str, Node], edges: list[Edge]):
        self.nodes = nodes
        self.adj: dict[str, list[Edge]] = {nid: [] for nid in nodes}
        self._edges: dict[tuple[str, str], Edge] = {}
        for e in edges:
            if e.source not in nodes or e.target not in nodes:
                raise ValueError(f"edge {e.source}->{e.target} references unknown node")
            if e.axis not in ("NS", "EW"):
                raise ValueError(f"edge {e.source}->{e.target} has invalid axis {e.axis!r}")
            if e.length_m <= 0 or e.speed_kmh <= 0:
                raise ValueError(f"edge {e.source}->{e.target} has non-positive length/speed")
            self.adj[e.source].append(e)
            self._edges[(e.source, e.target)] = e

    @classmethod
    def from_dict(cls, data: dict) -> "Graph":
        nodes = {}
        for n in data["nodes"]:
            sig = Signal(**n["signal"]) if n.get("signal") else None
            nodes[n["id"]] = Node(n["id"], n["lat"], n["lon"], sig)
        edges = [Edge(**e) for e in data["edges"]]
        return cls(nodes, edges)

    @classmethod
    def load(cls, path: str | Path) -> "Graph":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def edge(self, source: str, target: str) -> Edge:
        return self._edges[(source, target)]

    def nearest_node(self, lat: float, lon: float) -> tuple[str, float]:
        best_id, best_d = "", float("inf")
        for n in self.nodes.values():
            d = haversine_m(lat, lon, n.lat, n.lon)
            if d < best_d:
                best_id, best_d = n.id, d
        return best_id, best_d

    def signalized_nodes(self) -> list[str]:
        return [n.id for n in self.nodes.values() if n.signal is not None]
