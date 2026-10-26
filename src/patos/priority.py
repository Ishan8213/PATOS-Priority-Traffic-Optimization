"""Emergency-vehicle priority *recommendations*.

This system controls no signal. For an authorized emergency vehicle it lists the
signals where the vehicle would otherwise wait and estimates the ETA if the
traffic authority granted green at those moments. Nothing here tells any vehicle
to disregard a signal.
"""
from __future__ import annotations

from .routing import Route, evaluate_path

EMERGENCY_VEHICLE_TYPES = frozenset({"AMBULANCE", "FIRE_TRUCK", "POLICE"})
AUTHORIZED_GROUP = "emergency_operator"


def parse_groups(claims: dict | None) -> set[str]:
    """Parse the cognito:groups claim, which API Gateway may deliver as
    'a,b', '[a b]' or '[a, b]'."""
    raw = (claims or {}).get("cognito:groups")
    if not raw:
        return set()
    if isinstance(raw, (list, tuple, set)):
        return {str(g) for g in raw}
    cleaned = str(raw).strip().strip("[]")
    return {g for g in cleaned.replace(",", " ").split() if g}


def evaluate_priority(graph, route: Route, vehicle_type: str, groups: set[str], congestion, cycle_starts):
    """Return a priority block for the response."""
    if vehicle_type not in EMERGENCY_VEHICLE_TYPES:
        return {"status": "NOT_APPLICABLE"}
    if AUTHORIZED_GROUP not in groups:
        return {
            "status": "DENIED_NOT_AUTHORIZED",
            "note": "Emergency vehicle type requested without emergency_operator authorization; "
            "routed as an ordinary vehicle.",
        }
    requests = [p for p in route.signal_passes if p.wait_s > 0]
    preempt = frozenset(p.intersection_id for p in requests)
    granted = evaluate_path(graph, route.nodes, route.depart_ts, congestion, cycle_starts, preempt)
    return {
        "status": "RECOMMENDED",
        "note": "Advisory only. No signal is controlled by this system; each request must be "
        "granted by the responsible traffic authority.",
        "requests": [
            {
                "intersection_id": p.intersection_id,
                "expected_arrival_ts": round(p.arrival_ts, 1),
                "expected_wait_without_priority_s": round(p.wait_s, 1),
            }
            for p in requests
        ],
        "eta_s_if_all_granted": round(granted.eta_s, 1),
        "time_saved_s_if_all_granted": round(route.eta_s - granted.eta_s, 1),
    }
