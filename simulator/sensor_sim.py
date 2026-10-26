"""Simulated intersection sensors publishing to AWS IoT Core.

Publishes with SigV4 over HTTPS through the IoT data plane, using whatever AWS
credentials your CLI profile / SSO session provides. No device certificates and
no access keys are stored in this repo.

  python simulator/sensor_sim.py --region <region> --rounds 5 --interval 10
  python simulator/sensor_sim.py --dry-run          # prints payloads, touches no AWS service
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from patos.graph import Graph  # noqa: E402

GRAPH_PATH = Path(__file__).resolve().parents[1] / "src/patos/data/city_graph.json"


def build_payloads(graph: Graph, now: float, rng: random.Random, load: float) -> list[tuple[str, dict]]:
    out = []
    for nid in graph.signalized_nodes():
        sig = graph.nodes[nid].signal
        cycle_start = now - ((now - sig.offset_s) % sig.cycle_s)  # start of current cycle
        count = max(0, int(rng.gauss(mu=30 * load, sigma=8)))
        out.append(
            (
                f"patos/telemetry/{nid}",
                {"intersection_id": nid, "vehicle_count": count, "cycle_start_ts": round(cycle_start, 3)},
            )
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--load", type=float, default=0.8, help="0..2, scales simulated traffic")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    graph = Graph.load(GRAPH_PATH)
    rng = random.Random(args.seed)
    client = None
    if not args.dry_run:
        import boto3

        iot = boto3.client("iot", region_name=args.region)
        endpoint = iot.describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]
        client = boto3.client("iot-data", region_name=args.region, endpoint_url=f"https://{endpoint}")

    for r in range(args.rounds):
        payloads = build_payloads(graph, time.time(), rng, args.load)
        for topic, payload in payloads:
            if client is None:
                print(topic, json.dumps(payload))
            else:
                client.publish(topic=topic, qos=1, payload=json.dumps(payload))
        print(f"round {r + 1}/{args.rounds}: {len(payloads)} messages {'(dry run)' if client is None else 'published'}")
        if r + 1 < args.rounds:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
