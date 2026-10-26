from patos.graph import Graph
from patos.priority import AUTHORIZED_GROUP, evaluate_priority, parse_groups
from patos.routing import find_routes

T0 = 1_800_000_000.0
G = Graph.load("src/patos/data/city_graph.json")


def test_parse_groups_variants():
    assert parse_groups({"cognito:groups": "a,b"}) == {"a", "b"}
    assert parse_groups({"cognito:groups": "[a b]"}) == {"a", "b"}
    assert parse_groups({"cognito:groups": "[a, b]"}) == {"a", "b"}
    assert parse_groups({"cognito:groups": ["emergency_operator"]}) == {"emergency_operator"}
    assert parse_groups({}) == set() and parse_groups(None) == set()


def _fastest():
    # find a departure with at least one wait so priority has something to request
    for offset in range(0, 90, 7):
        r = find_routes(G, "N_0_0", "N_5_5", T0 + offset, k=1)[0]
        if r.wait_s > 0:
            return r
    raise AssertionError("expected at least one departure with a signal wait")


def test_ordinary_vehicle_gets_no_priority():
    assert evaluate_priority(G, _fastest(), "CAR", {AUTHORIZED_GROUP}, {}, {})["status"] == "NOT_APPLICABLE"


def test_unauthorized_emergency_request_is_denied():
    p = evaluate_priority(G, _fastest(), "AMBULANCE", {"driver"}, {}, {})
    assert p["status"] == "DENIED_NOT_AUTHORIZED" and "requests" not in p


def test_authorized_emergency_gets_advisory_requests_and_savings():
    route = _fastest()
    p = evaluate_priority(G, route, "AMBULANCE", {AUTHORIZED_GROUP}, {}, {})
    assert p["status"] == "RECOMMENDED"
    assert "Advisory only" in p["note"]
    waits = [s for s in route.signal_passes if s.wait_s > 0]
    assert len(p["requests"]) == len(waits) > 0
    assert p["eta_s_if_all_granted"] < route.eta_s
    assert p["time_saved_s_if_all_granted"] > 0
