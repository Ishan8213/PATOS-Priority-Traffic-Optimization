import json
import threading
import urllib.error
import urllib.request

import pytest

from edge.video_counter import post_telemetry, summarize, update_tracks
from local.server import create_server


@pytest.fixture(scope="module")
def srv():
    httpd, engine = create_server(port=0, simulate=False, interval_s=3600)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", engine
    httpd.shutdown()
    engine.stop()
    httpd.server_close()


def call(base, path, body=None, role=None, host=None):
    headers = {"Content-Type": "application/json"}
    if role:
        headers["X-Demo-Role"] = role
    if host:
        headers["Host"] = host
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


ROUTE = {"origin": {"node_id": "N_0_0"}, "destination": {"node_id": "N_5_5"}, "vehicle_type": "CAR"}


def test_index_and_graph_and_state(srv):
    base, _ = srv
    status, html = call(base, "/")
    assert status == 200 and b"PATOS" in html
    status, g = call(base, "/api/graph")
    g = json.loads(g)
    assert status == 200 and len(g["nodes"]) == 36 and sum(n["signalized"] for n in g["nodes"]) == 16
    status, st = call(base, "/api/state")
    st = json.loads(st)
    assert status == 200 and len(st["signals"]) == 16 and all(s["fresh"] for s in st["signals"])


def test_route_for_driver_has_timeline_and_no_priority(srv):
    base, _ = srv
    status, body = call(base, "/api/route", ROUTE, role="driver")
    r = json.loads(body)
    assert status == 200 and r["priority"]["status"] == "NOT_APPLICABLE"
    tl = r["fastest"]["timeline"]
    assert tl[0]["node_id"] == "N_0_0" and tl[-1]["node_id"] == "N_5_5"
    assert all(b["arrive_ts"] >= a["depart_ts"] for a, b in zip(tl, tl[1:]))
    assert abs(tl[-1]["arrive_ts"] - r["fastest"]["arrival_ts"]) < 0.2


def test_roles_control_priority(srv):
    base, _ = srv
    amb = {**ROUTE, "vehicle_type": "AMBULANCE"}
    _, b1 = call(base, "/api/route", amb, role="driver")
    _, b2 = call(base, "/api/route", amb, role="emergency_operator")
    _, b3 = call(base, "/api/route", amb, role="hacker")  # unknown role falls back to driver
    assert json.loads(b1)["priority"]["status"] == "DENIED_NOT_AUTHORIZED"
    assert json.loads(b2)["priority"]["status"] == "RECOMMENDED"
    assert json.loads(b3)["priority"]["status"] == "DENIED_NOT_AUTHORIZED"


def test_audit_records_requests(srv):
    base, _ = srv
    call(base, "/api/route", ROUTE, role="driver")
    st = json.loads(call(base, "/api/state")[1])
    assert st["audit"] and st["audit"][0]["user_sub"] == "local-driver"


def test_bad_route_input_is_400(srv):
    base, _ = srv
    status, _ = call(base, "/api/route", {**ROUTE, "vehicle_type": "TANK"})
    assert status == 400


def test_telemetry_endpoint_validates(srv):
    base, _ = srv
    assert call(base, "/api/telemetry", {"intersection_id": "N_2_2", "vehicle_count": 77})[0] == 200
    assert call(base, "/api/telemetry", {"intersection_id": "N_2_2", "vehicle_count": -5})[0] == 400
    assert call(base, "/api/telemetry", {"intersection_id": "NOPE", "vehicle_count": 5})[0] == 400
    assert call(base, "/api/telemetry", ["x"])[0] == 400
    sig = next(s for s in json.loads(call(base, "/api/state")[1])["signals"] if s["id"] == "N_2_2")
    assert sig["vehicle_count"] == 77 and sig["level"] == "HIGH"


def test_high_congestion_telemetry_changes_the_route_eta(srv):
    base, _ = srv
    for nid in ("N_1_1", "N_1_2", "N_2_2", "N_3_3", "N_4_4"):
        call(base, "/api/telemetry", {"intersection_id": nid, "vehicle_count": 5})
    quiet = json.loads(call(base, "/api/route", ROUTE)[1])["fastest"]["eta_s"]
    for nid in ("N_1_1", "N_1_2", "N_2_2", "N_3_3", "N_4_4"):
        call(base, "/api/telemetry", {"intersection_id": nid, "vehicle_count": 90})
    busy = json.loads(call(base, "/api/route", ROUTE)[1])["fastest"]["eta_s"]
    assert busy >= quiet  # congestion never makes the best route faster


def test_simulator_controls(srv):
    base, engine = srv
    status, body = call(base, "/api/simulator", {"running": True, "load": 5})
    assert status == 200 and json.loads(body) == {"running": True, "load": 2.0, "interval_s": 3600}
    call(base, "/api/simulator", {"running": False})
    assert engine.running is False
    assert call(base, "/api/simulator", {"load": "abc"})[0] == 400


def test_foreign_host_header_is_rejected(srv):
    base, _ = srv
    assert call(base, "/api/state", host="evil.example.com")[0] == 403


def test_oversized_body_is_rejected(srv):
    base, _ = srv
    assert call(base, "/api/route", {"x": "a" * 20_000})[0] == 400


def test_unknown_paths_404(srv):
    assert call(srv[0], "/etc/passwd")[0] == 404


# ---- optional video counter (logic only; YOLO itself is not run in tests) ----
def test_video_counter_unique_tracking():
    seen = {}
    update_tracks(seen, [1, 2, 3], [2, 7, 0])        # car, truck, person (ignored)
    update_tracks(seen, [1, 2, 4], [2, 7, 5])        # same car/truck again, new bus
    update_tracks(seen, None, [])                    # frame with no tracks
    assert summarize(seen) == {"total": 3, "car": 1, "motorcycle": 0, "bus": 1, "truck": 1}


def test_video_counter_posts_to_server(srv):
    base, _ = srv
    res = post_telemetry(base + "/api/telemetry", "N_3_3", 12)
    assert res.get("stored") is True
    bad = post_telemetry(base + "/api/telemetry", "N_0_0", 12)  # not a signalized node
    assert bad.get("stored") is False
