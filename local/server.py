"""Local, no-AWS server: runs the SAME ingest/route handler code used in the cloud version.

It binds to 127.0.0.1 only. The "role" selector in the UI is a local stand-in for Amazon
Cognito groups and is NOT a security control.
"""
import json
import os
from decimal import Decimal
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("STALE_AFTER_S", "300")

from handlers import ingest, route  # noqa: E402  (src/ is added to sys.path by run_local.py)
from patos.routing import congestion_level  # noqa: E402
from simulator.sensor_sim import build_payloads  # noqa: E402

from .store import MirroredTable  # noqa: E402

INDEX = ROOT / "local" / "static" / "index.html"
MAX_BODY = 10_000


def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    raise TypeError(f"not JSON serializable: {type(o).__name__}")
ROLES = {"driver", "emergency_operator"}


class Engine:
    def __init__(self, load: float = 0.8, interval_s: float = 5.0, simulate: bool = True, aws=None):
        self.aws = aws
        self.telemetry = MirroredTable("intersection_id", on_put=aws.note_telemetry if aws else None)
        self.audit = MirroredTable("request_id", max_items=500, on_put=aws.enqueue_audit if aws else None)
        route._tables = lambda: (self.telemetry, self.audit)
        ingest._get_table = lambda: self.telemetry
        self.load, self.interval_s = load, interval_s
        self.running = simulate
        self._rng = random.Random(1)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self.publish_round()  # data is available immediately
        self._thread.start()

    def publish_round(self) -> int:
        n = 0
        for topic, payload in build_payloads(ingest.GRAPH, time.time(), self._rng, self.load):
            ingest.handler({**payload, "topic_intersection": topic.split("/")[2]}, None)
            n += 1
        return n

    def _loop(self):
        while not self._stop.wait(self.interval_s):
            if self.running:
                self.publish_round()

    def stop(self):
        self._stop.set()
        if self.aws:
            self.aws.stop()

    def state(self) -> dict:
        now = time.time()
        stale = float(os.environ["STALE_AFTER_S"])
        items = {i["intersection_id"]: i for i in self.telemetry.scan()["Items"]}
        sigs = []
        for nid in ingest.GRAPH.signalized_nodes():
            sig = ingest.GRAPH.nodes[nid].signal
            it = items.get(nid)
            age = now - float(it["received_ts"]) if it else None
            fresh = it is not None and age <= stale
            sigs.append({
                "id": nid, "cycle_s": sig.cycle_s, "ns_green_s": sig.ns_green_s, "ew_green_s": sig.ew_green_s,
                "cycle_start": float(it["cycle_start_ts"]) if fresh and "cycle_start_ts" in it else sig.offset_s,
                "vehicle_count": int(it["vehicle_count"]) if fresh else None,
                "level": congestion_level(float(it["vehicle_count"]))[1] if fresh else None,
                "fresh": fresh, "age_s": round(age, 1) if age is not None else None,
            })
        audit = [{k: a.get(k) for k in ("request_id", "ts", "user_sub", "vehicle_type", "origin",
                                        "destination", "fastest_eta_s", "priority_status")}
                 for a in self.audit.recent(15)]
        return {"server_ts": now, "simulator": {"running": self.running, "load": self.load,
                                                "interval_s": self.interval_s},
                "aws": self.aws.status() if self.aws else {"enabled": False},
                "signals": sigs, "audit": audit}


def graph_payload() -> dict:
    g = ingest.GRAPH
    return {
        "nodes": [{"id": n.id, "lat": n.lat, "lon": n.lon, "signalized": n.signal is not None}
                  for n in g.nodes.values()],
        "edges": [{"source": e.source, "target": e.target, "speed_kmh": e.speed_kmh}
                  for es in g.adj.values() for e in es if e.source < e.target],
    }


def make_handler(engine: Engine, port_getter):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PatosLocal/1.0"

        def log_message(self, fmt, *args):  # keep the console quiet
            pass

        def _json(self, status: int, obj) -> None:
            body = obj if isinstance(obj, (bytes, str)) else json.dumps(obj, default=_json_default)
            data = body.encode() if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _host_ok(self) -> bool:  # basic DNS-rebinding protection
            host = (self.headers.get("Host") or "").lower()
            return host in {f"127.0.0.1:{port_getter()}", f"localhost:{port_getter()}"}

        def _read_json(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None, "bad Content-Length"
            if n > MAX_BODY:
                return None, "request body too large"
            raw = self.rfile.read(n).decode("utf-8", "replace")
            return raw, ""

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "forbidden host"})
            if self.path in ("/", "/index.html"):
                data = INDEX.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
                self.end_headers()
                self.wfile.write(data)
            elif self.path == "/api/graph":
                self._json(200, graph_payload())
            elif self.path == "/api/state":
                self._json(200, engine.state())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._host_ok():
                return self._json(403, {"error": "forbidden host"})
            raw, err = self._read_json()
            if err:
                return self._json(400, {"error": err})
            if self.path == "/api/route":
                role = self.headers.get("X-Demo-Role", "driver")
                role = role if role in ROLES else "driver"
                event = {"body": raw, "requestContext": {"authorizer": {"claims": {
                    "sub": f"local-{role}", "cognito:groups": role}}}}
                res = route.handler(event, None)
                self._json(res["statusCode"], res["body"])
            elif self.path == "/api/telemetry":
                try:
                    payload = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    return self._json(400, {"error": "invalid JSON"})
                if not isinstance(payload, dict):
                    return self._json(400, {"error": "body must be an object"})
                res = ingest.handler({**payload, "topic_intersection": payload.get("intersection_id")}, None)
                self._json(200 if res.get("stored") else 400, res)
            elif self.path == "/api/simulator":
                try:
                    cfg = json.loads(raw or "{}")
                    if "running" in cfg:
                        engine.running = bool(cfg["running"])
                    if "load" in cfg:
                        engine.load = min(2.0, max(0.0, float(cfg["load"])))
                except (ValueError, TypeError):
                    return self._json(400, {"error": "invalid simulator settings"})
                self._json(200, engine.state()["simulator"])
            else:
                self._json(404, {"error": "not found"})

    return Handler


def create_server(port: int = 8000, simulate: bool = True, interval_s: float = 5.0, aws=None):
    engine = Engine(simulate=simulate, interval_s=interval_s, aws=aws)
    box = {}
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(engine, lambda: box["port"]))
    httpd.daemon_threads = True
    box["port"] = httpd.server_address[1]
    return httpd, engine
