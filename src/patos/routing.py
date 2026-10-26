"""Signal-aware, time-dependent routing.

Edge cost = base travel time x congestion multiplier of the downstream
intersection, plus the legal wait at that intersection's signal for the axis the
vehicle approaches on. Waiting never lets a vehicle arrive earlier, so the FIFO
property holds and a Dijkstra search on earliest-departure time is valid.
Turn movements and turn-specific phases are NOT modeled.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Mapping

from .graph import Graph
from .signals import phase_at, wait_s

# (upper bound of vehicle_count, travel-time multiplier, label). Prototype values, uncalibrated.
CONGESTION_LEVELS = ((10, 1.0, "LOW"), (25, 1.3, "MEDIUM"), (float("inf"), 1.8, "HIGH"))


def congestion_level(vehicle_count: float) -> tuple[float, str]:
    for upper, mult, label in CONGESTION_LEVELS:
        if vehicle_count < upper:
            return mult, label
    return CONGESTION_LEVELS[-1][1], CONGESTION_LEVELS[-1][2]


@dataclass
class SignalPass:
    intersection_id: str
    axis: str
    arrival_ts: float
    phase_on_arrival: str
    wait_s: float
    departure_ts: float
    preempted: bool = False

    def to_dict(self) -> dict:
        return {
            "intersection_id": self.intersection_id,
            "approach_axis": self.axis,
            "arrival_ts": round(self.arrival_ts, 1),
            "phase_on_arrival": self.phase_on_arrival,
            "wait_s": round(self.wait_s, 1),
            "departure_ts": round(self.departure_ts, 1),
            "priority_assumed": self.preempted,
        }


@dataclass
class Route:
    nodes: list[str]
    distance_m: float
    travel_s: float
    wait_s: float
    depart_ts: float
    arrival_ts: float
    signal_passes: list[SignalPass] = field(default_factory=list)
    timeline: list = field(default_factory=list)  # (node_id, arrive_ts, depart_ts)

    @property
    def eta_s(self) -> float:
        return self.arrival_ts - self.depart_ts

    def to_dict(self, graph: Graph | None = None) -> dict:
        d = {
            "nodes": self.nodes,
            "distance_m": round(self.distance_m, 1),
            "eta_s": round(self.eta_s, 1),
            "driving_s": round(self.travel_s, 1),
            "signal_wait_s": round(self.wait_s, 1),
            "arrival_ts": round(self.arrival_ts, 1),
            "signals": [p.to_dict() for p in self.signal_passes],
            "timeline": [
                {"node_id": n, "arrive_ts": round(a, 1), "depart_ts": round(d, 1)}
                for n, a, d in self.timeline
            ],
        }
        if graph is not None:
            d["path"] = [
                {"node_id": n, "lat": graph.nodes[n].lat, "lon": graph.nodes[n].lon}
                for n in self.nodes
            ]
        return d


def _traverse(graph, edge, depart_ts, congestion, cycle_starts, is_dest, preempt, penalty=1.0):
    travel = edge.base_time_s * congestion.get(edge.target, 1.0)
    arrive = depart_ts + travel * penalty
    node = graph.nodes[edge.target]
    wait, phase = 0.0, None
    if node.signal is not None and not is_dest:
        cs = cycle_starts.get(node.id)
        phase, _ = phase_at(node.signal, edge.axis, arrive, cs)
        wait = 0.0 if node.id in preempt else wait_s(node.signal, edge.axis, arrive, cs)
    return travel, arrive, wait, phase


def _search(graph, origin, dest, depart_ts, congestion, cycle_starts, preempt, penalties):
    best = {origin: depart_ts}
    prev: dict[str, str] = {}
    heap = [(depart_ts, origin)]
    while heap:
        t, u = heapq.heappop(heap)
        if t > best.get(u, float("inf")):
            continue
        if u == dest:
            break
        for e in graph.adj[u]:
            pen = penalties.get((e.source, e.target), 1.0) if penalties else 1.0
            _, arrive, wait, _ = _traverse(
                graph, e, t, congestion, cycle_starts, e.target == dest, preempt, pen
            )
            dep = arrive + wait
            if dep < best.get(e.target, float("inf")):
                best[e.target] = dep
                prev[e.target] = u
                heapq.heappush(heap, (dep, e.target))
    if dest not in best:
        return None
    path = [dest]
    while path[-1] != origin:
        path.append(prev[path[-1]])
    return path[::-1]


def evaluate_path(graph, path, depart_ts, congestion, cycle_starts, preempt=frozenset()) -> Route:
    """Compute true (unpenalized) timing for a node path."""
    t = depart_ts
    travel_total = wait_total = dist = 0.0
    passes: list[SignalPass] = []
    timeline = [(path[0], depart_ts, depart_ts)]
    for i in range(len(path) - 1):
        e = graph.edge(path[i], path[i + 1])
        is_dest = i == len(path) - 2
        travel, arrive, wait, phase = _traverse(
            graph, e, t, congestion, cycle_starts, is_dest, preempt
        )
        dist += e.length_m
        travel_total += travel
        wait_total += wait
        if phase is not None:
            passes.append(
                SignalPass(e.target, e.axis, arrive, phase, wait, arrive + wait, e.target in preempt)
            )
        t = arrive + wait
        timeline.append((e.target, arrive, t))
    return Route(list(path), dist, travel_total, wait_total, depart_ts, t, passes, timeline)


def _edges(path):
    return {(path[i], path[i + 1]) for i in range(len(path) - 1)}


def find_routes(
    graph: Graph,
    origin: str,
    dest: str,
    depart_ts: float,
    congestion: Mapping[str, float] | None = None,
    cycle_starts: Mapping[str, float] | None = None,
    k: int = 3,
    penalty: float = 1.6,
    max_overlap: float = 0.7,
) -> list[Route]:
    """Return up to k routes sorted by ETA; routes[0] is the fastest."""
    congestion = congestion or {}
    cycle_starts = cycle_starts or {}
    if origin not in graph.nodes or dest not in graph.nodes:
        raise KeyError("unknown origin or destination node")
    if origin == dest:
        return [Route([origin], 0.0, 0.0, 0.0, depart_ts, depart_ts, [], [(origin, depart_ts, depart_ts)])]

    first = _search(graph, origin, dest, depart_ts, congestion, cycle_starts, frozenset(), None)
    if first is None:
        return []
    paths = [first]
    penalties: dict[tuple[str, str], float] = {}
    last = first
    for _ in range(k * 4):
        if len(paths) >= k:
            break
        for edge in _edges(last):
            penalties[edge] = penalties.get(edge, 1.0) * penalty
        cand = _search(graph, origin, dest, depart_ts, congestion, cycle_starts, frozenset(), penalties)
        if cand is None:
            break
        last = cand
        if cand in paths:
            continue
        ce = _edges(cand)
        if any(len(ce & _edges(p)) / max(1, min(len(ce), len(_edges(p)))) > max_overlap for p in paths):
            continue
        paths.append(cand)

    routes = [evaluate_path(graph, p, depart_ts, congestion, cycle_starts) for p in paths]
    routes.sort(key=lambda r: r.eta_s)
    return routes
