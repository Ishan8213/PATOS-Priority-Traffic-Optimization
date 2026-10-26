"""Reproducible local experiment: signal-aware routing vs a signal-ignorant baseline.

Baseline: pick the route that minimises driving time while ignoring signals, then evaluate that
route with the real (modeled) signal waits. Compared with the signal-aware route for the same
origin/destination/departure. Synthetic grid, modeled signals, no congestion telemetry.

  python scripts/benchmark.py --trials 1000 --seed 2026
"""
import argparse
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from patos.graph import Graph, Node  # noqa: E402
from patos.priority import evaluate_priority  # noqa: E402
from patos.routing import evaluate_path, find_routes  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=1000)
ap.add_argument("--seed", type=int, default=2026)
args = ap.parse_args()

g = Graph.load(ROOT / "src/patos/data/city_graph.json")
no_signals = Graph(
    {k: Node(n.id, n.lat, n.lon, None) for k, n in g.nodes.items()},
    [e for edges in g.adj.values() for e in edges],
)
rng = random.Random(args.seed)
ids, t0 = list(g.nodes), 1_800_000_000.0
aware, base, wait_a, wait_b, saved = [], [], [], [], []
better = worse = 0
for _ in range(args.trials):
    o, d = rng.sample(ids, 2)
    t = t0 + rng.uniform(0, 3600)
    a = find_routes(g, o, d, t, k=1)[0]
    b = evaluate_path(g, find_routes(no_signals, o, d, t, k=1)[0].nodes, t, {}, {})
    aware.append(a.eta_s); base.append(b.eta_s); wait_a.append(a.wait_s); wait_b.append(b.wait_s)
    better += a.eta_s < b.eta_s - 1e-6
    worse += a.eta_s > b.eta_s + 1e-6
    if a.wait_s > 0:
        p = evaluate_priority(g, a, "AMBULANCE", {"emergency_operator"}, {}, {})
        saved.append(p["time_saved_s_if_all_granted"])

n = args.trials
print(f"trials={n} seed={args.seed}")
print(f"mean ETA: signal-aware {st.mean(aware):.1f}s vs baseline {st.mean(base):.1f}s "
      f"({100 * (1 - st.mean(aware) / st.mean(base)):.1f}% lower)")
print(f"mean signal wait: signal-aware {st.mean(wait_a):.1f}s vs baseline {st.mean(wait_b):.1f}s")
print(f"signal-aware faster in {better} ({100 * better / n:.1f}%) trials, slower in {worse}")
if saved:
    print(f"emergency advisory: {len(saved)} trials with waits; mean time saved if all granted "
          f"{st.mean(saved):.1f}s, max {max(saved):.1f}s")
