"""Sign in to Cognito, call POST /route, print a summary, optionally write an HTML map.

The password is read from the PATOS_PASSWORD environment variable or an interactive
prompt. It is never accepted as a command-line argument or stored.

  python client/get_route.py --region R --client-id ID --api-url URL --username U \
      --from N_0_0 --to N_5_5 --vehicle CAR --html route.html
"""
import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sign_in(region: str, client_id: str, username: str, password: str) -> str:
    import boto3

    idp = boto3.client("cognito-idp", region_name=region)
    res = idp.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    if "AuthenticationResult" not in res:
        raise SystemExit(f"Sign-in needs a further step: {res.get('ChallengeName')}. "
                         "Set a permanent password first (see docs/DEPLOY.md).")
    return res["AuthenticationResult"]["IdToken"]  # the API authorizer expects the ID token


def call_api(api_url: str, token: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        api_url.rstrip("/") + "/route",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%H:%M:%S UTC")


def summarize(route: dict) -> None:
    print(f"  {route['label']}: ETA {route['eta_s']:.0f}s "
          f"(driving {route['driving_s']:.0f}s + signal waits {route['signal_wait_s']:.0f}s), "
          f"{route['distance_m']:.0f} m, {len(route['signals'])} signals")
    for s in route["signals"]:
        extra = f", waits {s['wait_s']:.0f}s" if s["wait_s"] > 0 else ""
        print(f"     {s['intersection_id']}: arrive {fmt(s['arrival_ts'])} on {s['phase_on_arrival']}{extra}")


def write_html(result: dict, out: Path) -> None:
    graph = json.loads((ROOT / "src/patos/data/city_graph.json").read_text())
    lats = [n["lat"] for n in graph["nodes"]]
    lons = [n["lon"] for n in graph["nodes"]]
    w, h, pad = 700, 700, 30

    def xy(lat, lon):
        x = pad + (lon - min(lons)) / (max(lons) - min(lons)) * (w - 2 * pad)
        y = h - pad - (lat - min(lats)) / (max(lats) - min(lats)) * (h - 2 * pad)
        return round(x, 1), round(y, 1)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
           '<rect width="100%" height="100%" fill="#fafafa"/>']
    pos = {n["id"]: xy(n["lat"], n["lon"]) for n in graph["nodes"]}
    for e in graph["edges"]:
        if e["source"] < e["target"]:
            (x1, y1), (x2, y2) = pos[e["source"]], pos[e["target"]]
            svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ddd" stroke-width="2"/>')
    palette = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]
    routes = [result["fastest"]] + result["alternatives"]
    for i, r in reversed(list(enumerate(routes))):
        pts = " ".join(f"{pos[p['node_id']][0]},{pos[p['node_id']][1]}" for p in r["path"])
        width = 6 if i == 0 else 3
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{palette[i % 4]}" stroke-width="{width}" '
                   f'stroke-opacity="{1 if i == 0 else 0.6}" stroke-linejoin="round"/>')
    for n in graph["nodes"]:
        x, y = pos[n["id"]]
        svg.append(f'<circle cx="{x}" cy="{y}" r="{5 if n.get("signal") else 3}" '
                   f'fill="{"#333" if n.get("signal") else "#999"}"/>')
    svg.append("</svg>")
    legend = "".join(
        f'<li style="color:{palette[i % 4]}"><b>{r["label"]}</b>: {r["eta_s"]:.0f}s ETA, '
        f'{r["signal_wait_s"]:.0f}s waiting at signals</li>' for i, r in enumerate(routes))
    out.write_text(f"<!doctype html><meta charset=utf-8><title>PATOS route</title>"
                   f"<h2>PATOS route (demo data)</h2><ul>{legend}</ul>{''.join(svg)}"
                   f"<p><small>Dark dots are signalized intersections. {result['disclaimer']}</small></p>",
                   encoding="utf-8")


def point(value: str) -> dict:
    if "," in value:
        lat, lon = value.split(",", 1)
        return {"lat": float(lat), "lon": float(lon)}
    return {"node_id": value}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--api-url", required=True)
    ap.add_argument("--username", required=True)
    ap.add_argument("--from", dest="origin", required=True, help="node id (N_0_0) or 'lat,lon'")
    ap.add_argument("--to", dest="dest", required=True)
    ap.add_argument("--vehicle", default="CAR")
    ap.add_argument("--html", help="write an SVG map of the routes to this file")
    args = ap.parse_args()

    password = os.environ.get("PATOS_PASSWORD") or getpass.getpass("Password: ")
    token = sign_in(args.region, args.client_id, args.username, password)
    status, result = call_api(args.api_url, token,
                              {"origin": point(args.origin), "destination": point(args.dest),
                               "vehicle_type": args.vehicle})
    if status != 200:
        sys.exit(f"API returned {status}: {result}")
    q = result["data_quality"]
    print(f"Request {result['request_id']} ({result['vehicle_type']}); live telemetry at "
          f"{q['with_fresh_telemetry']}/{q['signalized_intersections']} signals")
    summarize(result["fastest"])
    for alt in result["alternatives"]:
        summarize(alt)
    print("Priority:", result["priority"]["status"])
    for r in result["priority"].get("requests", []):
        print(f"   request green at {r['intersection_id']} around {fmt(r['expected_arrival_ts'])}")
    if "eta_s_if_all_granted" in result["priority"]:
        print(f"   ETA if all granted: {result['priority']['eta_s_if_all_granted']:.0f}s (advisory only)")
    if args.html:
        write_html(result, Path(args.html))
        print("Wrote", args.html)


if __name__ == "__main__":
    main()
