"""Cloud side of the hybrid demo: the local app invokes this Lambda directly (no IoT Core,
no API Gateway) with a batch of sensor readings.

event: {"readings": [{"intersection_id": "N_2_2", "vehicle_count": 12, "cycle_start_ts": 1800000000.0}, ...]}
Each reading is validated with the same rules as handlers.ingest before it is stored.
"""
import logging
import time

from handlers import ingest

log = logging.getLogger()
log.setLevel(logging.INFO)
MAX_READINGS = 50


def handler(event, context):
    readings = event.get("readings") if isinstance(event, dict) else None
    if not isinstance(readings, list) or not readings:
        return {"stored": 0, "rejected": 0, "reason": "readings must be a non-empty list"}
    if len(readings) > MAX_READINGS:
        return {"stored": 0, "rejected": len(readings), "reason": f"at most {MAX_READINGS} readings per call"}
    now = time.time()
    table = ingest._get_table()
    stored = rejected = 0
    for r in readings:
        item, reason = (None, "not an object")
        if isinstance(r, dict):
            item, reason = ingest.validate({**r, "topic_intersection": r.get("intersection_id")}, now)
        if item is None:
            rejected += 1
            log.warning("rejected reading: %s", reason)
            continue
        table.put_item(Item=item)
        stored += 1
    return {"stored": stored, "rejected": rejected}
