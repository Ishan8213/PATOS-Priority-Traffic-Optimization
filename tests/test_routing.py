import pytest

from patos.graph import Edge, Graph, Node, Signal
from patos.routing import congestion_level, evaluate_path, find_routes

T0 = 1_800_000_000.0


def diamond(signal_on_top=True):
    """A -> B -> D (short, signal at B) and A -> C -> D (longer, no signal)."""
    sig = Signal(cycle_s=100, ns_green_s=10, ew_green_s=10, offset_s=0)
    nodes = {
        "A": Node("A", 0, 0), "D": Node("D", 0, 0.01),
        "B": Node("B", 0.001, 0.005, sig if signal_on_top else None),
        "C": Node("C", -0.001, 0.005),
    }
    e = []
    def both(a, b, length, speed, axis):
        e.append(Edge(a, b, length, speed, axis)); e.append(Edge(b, a, length, speed, axis))
    both("A", "B", 500, 36, "NS")   # 50 s
    both("B", "D", 500, 36, "EW")   # 50 s
    both("A", "C", 600, 36, "NS")   # 60 s
    both("C", "D", 600, 36, "NS")   # 60 s
    return Graph(nodes, e)


def test_no_signal_takes_shortest():
    r = find_routes(diamond(signal_on_top=False), "A", "D", T0, k=1)[0]
    assert r.nodes == ["A", "B", "D"] and r.eta_s == pytest.approx(100)


def test_red_signal_pushes_route_to_unsignalized_path():
    # Arrive at B at T0+50 -> NS window is [0,10) of a 100s cycle -> x=50 is red, wait 50s -> 150s total
    routes = find_routes(diamond(), "A", "D", T0, k=2)
    assert routes[0].nodes == ["A", "C", "D"]
    assert routes[0].eta_s == pytest.approx(120)
    via_b = [r for r in routes if r.nodes == ["A", "B", "D"]][0]
    assert via_b.wait_s == pytest.approx(50) and via_b.eta_s == pytest.approx(150)


def test_departure_time_changes_the_answer():
    # Depart 45s earlier relative to the cycle so we hit B just as NS turns green.
    g = diamond()
    r = find_routes(g, "A", "D", T0 + 50, k=1)[0]  # arrives B at x=100%100=0 -> green
    assert r.nodes == ["A", "B", "D"] and r.wait_s == 0


def test_signal_pass_details_recorded():
    g = diamond()
    r = evaluate_path(g, ["A", "B", "D"], T0, {}, {})
    assert len(r.signal_passes) == 1
    p = r.signal_passes[0]
    assert p.intersection_id == "B" and p.phase_on_arrival == "RED" and p.wait_s == pytest.approx(50)
    assert p.departure_ts == pytest.approx(p.arrival_ts + 50)


def test_destination_signal_is_not_waited_at():
    g = diamond()
    r = evaluate_path(g, ["A", "B"], T0, {}, {})
    assert r.wait_s == 0 and r.signal_passes == []


def test_congestion_multiplier_slows_edges():
    g = diamond(signal_on_top=False)
    fast = find_routes(g, "A", "D", T0, k=1)[0]
    slow = find_routes(g, "A", "D", T0, {"B": 3.0}, k=1)[0]
    assert slow.nodes == ["A", "C", "D"] and slow.eta_s > fast.eta_s


def test_cycle_start_from_telemetry_changes_wait():
    g = diamond()
    # Telemetry says B's cycle began 50s before T0, so NS is green when we arrive at T0+50.
    r = evaluate_path(g, ["A", "B", "D"], T0, {}, {"B": T0 + 50 - 100 * 1000})
    assert r.wait_s == 0


def test_preempt_removes_wait():
    g = diamond()
    r = evaluate_path(g, ["A", "B", "D"], T0, {}, {}, preempt=frozenset({"B"}))
    assert r.wait_s == 0 and r.signal_passes[0].preempted


def test_alternatives_are_distinct_and_sorted():
    routes = find_routes(diamond(), "A", "D", T0, k=3)
    assert len(routes) == 2  # only two simple paths exist
    assert routes[0].eta_s <= routes[1].eta_s
    assert routes[0].nodes != routes[1].nodes


def test_unreachable_returns_empty():
    g = diamond()
    g.nodes["Z"] = Node("Z", 1, 1)
    g.adj["Z"] = []
    assert find_routes(g, "A", "Z", T0) == []


def test_same_origin_destination():
    r = find_routes(diamond(), "A", "A", T0)
    assert len(r) == 1 and r[0].eta_s == 0


def test_unknown_node_raises():
    with pytest.raises(KeyError):
        find_routes(diamond(), "A", "NOPE", T0)


def test_congestion_levels():
    assert congestion_level(0)[1] == "LOW"
    assert congestion_level(10)[1] == "MEDIUM"
    assert congestion_level(25)[1] == "HIGH"


def test_city_graph_fastest_is_never_beaten_by_alternates():
    g = Graph.load("src/patos/data/city_graph.json")
    routes = find_routes(g, "N_0_0", "N_5_5", T0, k=3)
    assert len(routes) >= 2
    assert all(routes[0].eta_s <= r.eta_s + 1e-9 for r in routes)
    assert all(r.nodes[0] == "N_0_0" and r.nodes[-1] == "N_5_5" for r in routes)
