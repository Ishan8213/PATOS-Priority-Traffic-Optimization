"""Generate a deterministic synthetic city grid (no real-world roads).

Usage: python scripts/make_grid_graph.py [--size 6] [--out src/patos/data/city_graph.json]
Replace this file's output with a graph built from real map data for a real area.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from patos.graph import haversine_m  # noqa: E402

ANCHOR_LAT, ANCHOR_LON = 12.90, 77.60  # arbitrary anchor for the synthetic grid
SPACING_M = 400.0


def build(size: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    dlat = SPACING_M / 111_320.0
    dlon = SPACING_M / (111_320.0 * math.cos(math.radians(ANCHOR_LAT)))
    arterial_rows = {1, size - 2}  # faster east-west corridors
    nodes, edges = [], []
    for r in range(size):
        for c in range(size):
            nid = f"N_{r}_{c}"
            lat, lon = ANCHOR_LAT + r * dlat, ANCHOR_LON + c * dlon
            node = {"id": nid, "lat": round(lat, 6), "lon": round(lon, 6)}
            interior = 0 < r < size - 1 and 0 < c < size - 1
            if interior:
                cycle = rng.choice([60, 75, 90])
                ns = rng.choice([25, 30, 35])
                ew = rng.choice([20, 25, 30]) if r not in arterial_rows else ns + 10
                ew = min(ew, cycle - ns - 5)
                node["signal"] = {"cycle_s": cycle, "ns_green_s": ns, "ew_green_s": ew,
                                  "offset_s": rng.randrange(0, cycle)}
            nodes.append(node)
    coords = {n["id"]: (n["lat"], n["lon"]) for n in nodes}

    def add(a, b, axis, speed):
        length = haversine_m(*coords[a], *coords[b])
        edges.append({"source": a, "target": b, "length_m": round(length, 1),
                      "speed_kmh": speed, "axis": axis})

    for r in range(size):
        for c in range(size):
            a = f"N_{r}_{c}"
            if c + 1 < size:  # east-west street
                b = f"N_{r}_{c + 1}"
                spd = 60 if r in arterial_rows else 40
                add(a, b, "EW", spd)
                add(b, a, "EW", spd)
            if r + 1 < size:  # north-south street
                b = f"N_{r + 1}_{c}"
                add(a, b, "NS", 40)
                add(b, a, "NS", 40)
    return {"description": "Synthetic grid for demonstration; not real roads.", "nodes": nodes, "edges": edges}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=6)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "src/patos/data/city_graph.json"))
    args = ap.parse_args()
    data = build(args.size)
    Path(args.out).write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {args.out}: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
