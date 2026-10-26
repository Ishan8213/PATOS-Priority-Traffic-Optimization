import json
import random
import time
from decimal import Decimal

import pytest

from handlers import ingest, route
from simulator.sensor_sim import build_payloads


class FakeTable:
    def __init__(self):
        self.items = {}
        self.fail = False

    def put_item(self, Item):
        if self.fail:
            raise RuntimeError("boom")
        key = Item.get("intersection_id") or Item.get("request_id")
        self.items[key] = Item

    def scan(self, **_):
        return {"Items": list(self.items.values())}


@pytest.fixture
def tables(monkeypatch):
    telemetry, audit = FakeTable(), FakeTable()
    monkeypatch.setattr(route, "_tables", lambda: (telemetry, audit))
    monkeypatch.setattr(ingest, "_get_table", lambda: telemetry)
    return telemetry, audit


def event(body, groups=None, sub="user-1"):
    claims = {"sub": sub}
    if groups is not None:
        claims["cognito:groups"] = groups
    return {"body": json.dumps(body) if not isinstance(body, str) else body,
            "requestContext": {"authorizer": {"claims": claims}}}


BASE = {"origin": {"node_id": "N_0_0"}, "destination": {"node_id": "N_5_5"}, "vehicle_type": "CAR"}


# ---------- ingest ----------
def test_ingest_stores_valid_telemetry(tables):
    now = time.time()
    out = ingest.handler({"intersection_id": "N_2_2", "topic_intersection": "N_2_2",
                          "vehicle_count": 12, "cycle_start_ts": now - 20}, None)
    assert out["stored"] is True
    item = tables[0].items["N_2_2"]
    assert item["vehicle_count"] == 12 and isinstance(item["received_ts"], Decimal) and item["ttl"] > now


@pytest.mark.parametrize("bad", [
    {"intersection_id": "N_2_2", "topic_intersection": "N_3_3", "vehicle_count": 1},   # topic mismatch
    {"intersection_id": "N_0_0", "topic_intersection": "N_0_0", "vehicle_count": 1},   # not signalized
    {"intersection_id": "NOPE", "topic_intersection": "NOPE", "vehicle_count": 1},     # unknown
    {"intersection_id": "N_2_2", "topic_intersection": "N_2_2", "vehicle_count": -1},
    {"intersection_id": "N_2_2", "topic_intersection": "N_2_2", "vehicle_count": 10**6},
    {"intersection_id": "N_2_2", "topic_intersection": "N_2_2", "vehicle_count": True},
    {"intersection_id": "N_2_2", "topic_intersection": "N_2_2", "vehicle_count": 5, "cycle_start_ts": 1.0},
    {},
])
def test_ingest_rejects_invalid(tables, bad):
    assert ingest.handler(bad, None)["stored"] is False
    assert tables[0].items == {}


def test_simulator_payloads_pass_ingest_validation(tables):
    now = time.time()
    payloads = build_payloads(ingest.GRAPH, now, random.Random(3), 1.0)
    assert len(payloads) == len(ingest.GRAPH.signalized_nodes())
    for topic, payload in payloads:
        out = ingest.handler({**payload, "topic_intersection": topic.split("/")[2]}, None)
        assert out["stored"] is True, (topic, payload)


# ---------- route ----------
def test_route_ok_with_no_telemetry(tables):
    r = route.handler(event(BASE), None)
    body = json.loads(r["body"])
    assert r["statusCode"] == 200
    assert body["fastest"]["label"] == "FASTEST" and body["fastest"]["eta_s"] > 0
    assert body["data_quality"]["with_fresh_telemetry"] == 0
    assert body["priority"]["status"] == "NOT_APPLICABLE"
    assert "disclaimer" in body
    assert len(tables[1].items) == 1  # audit record written


def test_route_uses_fresh_telemetry_and_ignores_stale(tables):
    now = time.time()
    for iid, age in (("N_1_1", 10), ("N_2_2", 10_000)):
        ingest.handler({"intersection_id": iid, "topic_intersection": iid, "vehicle_count": 40}, None)
        tables[0].items[iid]["received_ts"] = Decimal(str(now - age))
    body = json.loads(route.handler(event(BASE), None)["body"])
    assert body["data_quality"]["with_fresh_telemetry"] == 1


def test_route_snaps_lat_lon(tables):
    n = route.GRAPH.nodes["N_0_0"]
    body = {**BASE, "origin": {"lat": n.lat + 0.0001, "lon": n.lon}}
    r = route.handler(event(body), None)
    out = json.loads(r["body"])
    assert r["statusCode"] == 200 and out["origin"]["node_id"] == "N_0_0"
    assert 0 < out["origin"]["snap_distance_m"] < 50


@pytest.mark.parametrize("body", [
    "not json", "[]", {}, {**BASE, "vehicle_type": "TANK"},
    {**BASE, "origin": {"node_id": "NOPE"}}, {**BASE, "origin": {"lat": 0, "lon": 0}},
    {**BASE, "origin": {"lat": "x", "lon": 1}}, {**BASE, "origin": "N_0_0"},
    {**BASE, "depart_at": 5}, {**BASE, "depart_at": True}, "x" * 5000,
])
def test_route_rejects_bad_input(tables, body):
    assert route.handler(event(body), None)["statusCode"] == 400


def test_route_ordinary_user_cannot_get_priority(tables):
    r = json.loads(route.handler(event({**BASE, "vehicle_type": "AMBULANCE"}, groups="driver"), None)["body"])
    assert r["priority"]["status"] == "DENIED_NOT_AUTHORIZED"


def test_route_authorized_emergency_is_audited(tables):
    body = None
    for off in range(0, 90, 7):  # find a departure with at least one wait
        r = route.handler(event({**BASE, "vehicle_type": "AMBULANCE", "depart_at": time.time() + off},
                                groups="[emergency_operator]"), None)
        body = json.loads(r["body"])
        if body["priority"].get("requests"):
            break
    assert body["priority"]["status"] == "RECOMMENDED" and body["priority"]["requests"]
    audit = [i for i in tables[1].items.values() if i["priority_status"] == "RECOMMENDED"]
    assert audit and audit[-1]["user_sub"] == "user-1" and audit[-1]["priority_requested_at"]


def test_priority_fails_closed_when_audit_unavailable(tables):
    tables[1].fail = True
    for off in range(0, 90, 7):
        r = route.handler(event({**BASE, "vehicle_type": "AMBULANCE", "depart_at": time.time() + off},
                                groups="emergency_operator"), None)
        if r["statusCode"] == 500:
            assert "priority" not in json.loads(r["body"])
            return
    pytest.fail("expected a 500 when an authorized priority request cannot be audited")


def test_ordinary_route_survives_audit_failure(tables):
    tables[1].fail = True
    assert route.handler(event(BASE), None)["statusCode"] == 200
