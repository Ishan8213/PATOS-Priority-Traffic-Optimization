"""API Gateway (Cognito-authorized) -> Lambda: POST /route.

Request body:
  {"origin": {"node_id": "N_0_0"} | {"lat": .., "lon": ..},
   "destination": {...same...},
   "vehicle_type": "CAR|BUS|TRUCK|MOTORCYCLE|AMBULANCE|FIRE_TRUCK|POLICE",
   "depart_at": <optional epoch seconds, within +/-1h of now>}
"""
import json
import logging
import os
import time
import uuid
from decimal import Decimal
from pathlib import Path

from patos.graph import Graph
from patos.priority import EMERGENCY_VEHICLE_TYPES, evaluate_priority, parse_groups
from patos.routing import congestion_level, find_routes

log = logging.getLogger()
log.setLevel(logging.INFO)

GRAPH = Graph.load(Path(__file__).resolve().parent.parent / "patos" / "data" / "city_graph.json")
VEHICLE_TYPES = {"CAR", "BUS", "TRUCK", "MOTORCYCLE"} | set(EMERGENCY_VEHICLE_TYPES)
MAX_BODY_CHARS = 4000
MAX_SNAP_M = 2000.0
AUDIT_TTL_S = 30 * 86_400
DISCLAIMER = (
    "Demonstration output based on simulated/modeled data. Signal timing is a modeled fixed-time "
    "plan; routes are planning estimates and do not authorize any driver to disregard a traffic "
    "signal or the law."
)

_dynamodb = None


def _tables():
    global _dynamodb
    if _dynamodb is None:
        import boto3

        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(os.environ["TELEMETRY_TABLE"]), _dynamodb.Table(os.environ["AUDIT_TABLE"])


class BadRequest(Exception):
    pass


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _resolve_point(spec, label: str) -> tuple[str, float]:
    if not isinstance(spec, dict):
        raise BadRequest(f"{label} must be an object")
    if "node_id" in spec:
        nid = spec["node_id"]
        if not isinstance(nid, str) or nid not in GRAPH.nodes:
            raise BadRequest(f"{label}.node_id is unknown")
        return nid, 0.0
    lat, lon = spec.get("lat"), spec.get("lon")
    ok = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (lat, lon))
    if not ok or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise BadRequest(f"{label} needs node_id or valid lat/lon")
    nid, dist = GRAPH.nearest_node(lat, lon)
    if dist > MAX_SNAP_M:
        raise BadRequest(f"{label} is more than {int(MAX_SNAP_M)} m from the mapped area")
    return nid, dist


def _parse(event: dict, now: float):
    raw = event.get("body") or ""
    if len(raw) > MAX_BODY_CHARS:
        raise BadRequest("request body too large")
    try:
        body = json.loads(raw or "{}")
    except json.JSONDecodeError:
        raise BadRequest("body is not valid JSON")
    if not isinstance(body, dict):
        raise BadRequest("body must be a JSON object")
    vtype = body.get("vehicle_type", "CAR")
    if vtype not in VEHICLE_TYPES:
        raise BadRequest("vehicle_type must be one of " + ", ".join(sorted(VEHICLE_TYPES)))
    origin, o_snap = _resolve_point(body.get("origin"), "origin")
    dest, d_snap = _resolve_point(body.get("destination"), "destination")
    depart = body.get("depart_at", now)
    if not isinstance(depart, (int, float)) or isinstance(depart, bool) or abs(depart - now) > 3600:
        raise BadRequest("depart_at must be epoch seconds within 1 hour of now")
    return vtype, origin, o_snap, dest, d_snap, float(depart)


def _load_live_state(now: float):
    table, _ = _tables()
    stale_after = float(os.environ.get("STALE_AFTER_S", "300"))
    items, kwargs = [], {}
    while True:
        page = table.scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    congestion, cycle_starts = {}, {}
    for it in items:
        iid = it.get("intersection_id")
        if iid not in GRAPH.nodes or now - float(it.get("received_ts", 0)) > stale_after:
            continue
        mult, _ = congestion_level(float(it.get("vehicle_count", 0)))
        congestion[iid] = mult
        if it.get("cycle_start_ts") is not None:
            cycle_starts[iid] = float(it["cycle_start_ts"])
    return congestion, cycle_starts


def _audit(record: dict) -> None:
    _, audit = _tables()
    audit.put_item(Item=json.loads(json.dumps(record), parse_float=Decimal))


def handler(event, context):
    now = time.time()
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("claims") or {}
    groups = parse_groups(claims)
    try:
        vtype, origin, o_snap, dest, d_snap, depart = _parse(event, now)
    except BadRequest as e:
        return _resp(400, {"error": str(e)})

    try:
        congestion, cycle_starts = _load_live_state(now)
        routes = find_routes(GRAPH, origin, dest, depart, congestion, cycle_starts)
    except Exception:
        log.exception("routing failed")
        return _resp(500, {"error": "internal error"})
    if not routes:
        return _resp(404, {"error": "no route found between origin and destination"})

    fastest = routes[0]
    priority = evaluate_priority(GRAPH, fastest, vtype, groups, congestion, cycle_starts)
    request_id = str(uuid.uuid4())
    record = {
        "request_id": request_id,
        "ts": int(now),
        "ttl": int(now) + AUDIT_TTL_S,
        "user_sub": claims.get("sub", "unknown"),
        "vehicle_type": vtype,
        "origin": origin,
        "destination": dest,
        "fastest_eta_s": round(fastest.eta_s, 1),
        "priority_status": priority["status"],
        "priority_requested_at": [r["intersection_id"] for r in priority.get("requests", [])],
    }
    try:
        _audit(record)
    except Exception:
        log.exception("audit write failed")
        if priority["status"] == "RECOMMENDED":  # fail closed: no unlogged priority requests
            return _resp(500, {"error": "could not record priority request; try again"})

    total = len(GRAPH.signalized_nodes())
    return _resp(
        200,
        {
            "request_id": request_id,
            "vehicle_type": vtype,
            "depart_ts": round(depart, 1),
            "origin": {"node_id": origin, "snap_distance_m": round(o_snap, 1)},
            "destination": {"node_id": dest, "snap_distance_m": round(d_snap, 1)},
            "fastest": {"label": "FASTEST", **fastest.to_dict(GRAPH)},
            "alternatives": [
                {"label": f"ALTERNATE_{i}", **r.to_dict(GRAPH)} for i, r in enumerate(routes[1:], 1)
            ],
            "priority": priority,
            "data_quality": {
                "signalized_intersections": total,
                "with_fresh_telemetry": len([i for i in congestion if GRAPH.nodes[i].signal]),
                "signal_timing": "modeled fixed-time plan; cycle start synced to telemetry where fresh",
                "telemetry_stale_after_s": float(os.environ.get("STALE_AFTER_S", "300")),
            },
            "disclaimer": DISCLAIMER,
        },
    )
