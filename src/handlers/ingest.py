"""IoT Core rule -> Lambda: validate telemetry and store the latest state per intersection.

Expected MQTT topic: patos/telemetry/<intersection_id>
Expected payload:
  {"intersection_id": "N_2_3", "vehicle_count": 12, "cycle_start_ts": 1800000000.0}
The IoT rule adds `topic_intersection` (third topic segment); it must match the payload.
"""
import json
import logging
import os
import time
from decimal import Decimal
from pathlib import Path

from patos.graph import Graph

log = logging.getLogger()
log.setLevel(logging.INFO)

GRAPH = Graph.load(Path(__file__).resolve().parent.parent / "patos" / "data" / "city_graph.json")
TTL_S = 3600
MAX_VEHICLES = 1000

_table = None


def _get_table():
    global _table
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(os.environ["TELEMETRY_TABLE"])
    return _table


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(event: dict, now: float) -> tuple[dict | None, str]:
    iid = event.get("intersection_id")
    if not isinstance(iid, str) or iid != event.get("topic_intersection"):
        return None, "intersection_id missing or does not match topic"
    node = GRAPH.nodes.get(iid)
    if node is None or node.signal is None:
        return None, "unknown or non-signalized intersection"
    vc = event.get("vehicle_count")
    if not _is_number(vc) or vc < 0 or vc > MAX_VEHICLES:
        return None, "vehicle_count must be a number between 0 and %d" % MAX_VEHICLES
    item = {"intersection_id": iid, "vehicle_count": int(vc), "received_ts": Decimal(str(round(now, 3)))}
    cs = event.get("cycle_start_ts")
    if cs is not None:
        if not _is_number(cs) or abs(now - cs) > 86_400:
            return None, "cycle_start_ts must be epoch seconds within 24h of now"
        item["cycle_start_ts"] = Decimal(str(round(cs, 3)))
    item["ttl"] = int(now) + TTL_S
    return item, ""


def handler(event, context):
    now = time.time()
    item, reason = validate(event if isinstance(event, dict) else {}, now)
    if item is None:
        log.warning("dropped telemetry: %s", reason)
        return {"stored": False, "reason": reason}
    _get_table().put_item(Item=item)
    return {"stored": True, "intersection_id": item["intersection_id"]}
