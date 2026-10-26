"""OPTIONAL, best-effort mirroring of the local demo to AWS using only Lambda and DynamoDB.

* Every audit record is written to a DynamoDB table.
* The latest sensor readings are sent in batches to a Lambda function that validates and stores them.
* The local app never depends on this: any AWS error is counted and shown in the UI, nothing more.
* Safety caps: telemetry is sent at most every `interval_s` seconds and at most `max_batches` times.

Uses your normal AWS CLI credentials (e.g. after `aws login`). No keys live in this project.
"""
import json
import threading
import time
from collections import deque
from decimal import Decimal

AUDIT_RETRIES = 3


def outputs_of(cfn, stack_name: str) -> dict:
    stacks = cfn.describe_stacks(StackName=stack_name)["Stacks"]
    stack = stacks[0]
    if stack["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        raise RuntimeError(f"stack {stack_name} is {stack['StackStatus']}, expected CREATE_COMPLETE")
    outs = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
    for key in ("AuditTableName", "IngestFunctionName"):
        if key not in outs:
            raise RuntimeError(f"stack {stack_name} has no output {key}; is it the hybrid stack?")
    return outs


def _num(v):
    return float(v) if isinstance(v, Decimal) and v != v.to_integral_value() else int(v) if isinstance(v, Decimal) else v


class AwsSync:
    def __init__(self, audit_table, lambda_client, ingest_function: str, interval_s: float = 15.0,
                 max_batches: int = 120, region: str = "", autostart: bool = True):
        self._audit_table, self._lambda, self._fn = audit_table, lambda_client, ingest_function
        self.interval_s, self.max_batches, self.region = interval_s, max_batches, region
        self._lock = threading.Lock()
        self._audit_q: deque = deque(maxlen=500)
        self._pending: dict = {}
        self._last_batch = 0.0
        self._s = {"audit_sent": 0, "audit_failed": 0, "telemetry_batches": 0, "telemetry_readings": 0,
                   "telemetry_rejected": 0, "paused": False, "last_ok_ts": None, "last_error": None}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        if autostart:
            self._thread.start()

    @classmethod
    def from_stack(cls, stack_name: str, region: str | None = None, **kw) -> "AwsSync":
        import boto3  # imported here so the local demo never needs boto3

        session = boto3.session.Session(region_name=region)
        outs = outputs_of(session.client("cloudformation"), stack_name)
        return cls(session.resource("dynamodb").Table(outs["AuditTableName"]), session.client("lambda"),
                   outs["IngestFunctionName"], region=session.region_name or "", **kw)

    # ---- callbacks used by the local tables ----
    def enqueue_audit(self, item: dict) -> None:
        with self._lock:
            self._audit_q.append((item, 0))

    def note_telemetry(self, item: dict) -> None:
        reading = {"intersection_id": item["intersection_id"], "vehicle_count": int(item["vehicle_count"])}
        if item.get("cycle_start_ts") is not None:
            reading["cycle_start_ts"] = float(item["cycle_start_ts"])
        with self._lock:
            self._pending[reading["intersection_id"]] = reading  # keep only the latest per intersection

    # ---- worker ----
    def _fail(self, what: str, e: Exception) -> None:
        with self._lock:
            self._s["last_error"] = f"{what}: {type(e).__name__}: {str(e)[:160]}"

    def _ok(self) -> None:
        with self._lock:
            self._s["last_ok_ts"] = time.time()
            self._s["last_error"] = None

    def flush(self, force: bool = False) -> None:
        with self._lock:
            audits = list(self._audit_q)
            self._audit_q.clear()
        for item, attempts in audits:
            try:
                self._audit_table.put_item(Item=item)
                with self._lock:
                    self._s["audit_sent"] += 1
                self._ok()
            except Exception as e:
                self._fail("audit", e)
                with self._lock:
                    if attempts + 1 < AUDIT_RETRIES:
                        self._audit_q.append((item, attempts + 1))
                    else:
                        self._s["audit_failed"] += 1
        now = time.time()
        with self._lock:
            due = bool(self._pending) and (force or now - self._last_batch >= self.interval_s)
            if due and self._s["telemetry_batches"] >= self.max_batches:
                self._s["paused"], self._pending, due = True, {}, False
            readings = list(self._pending.values()) if due else []
            if due:
                self._pending.clear()
                self._last_batch = now
        if readings:
            try:
                res = self._lambda.invoke(FunctionName=self._fn, InvocationType="RequestResponse",
                                          Payload=json.dumps({"readings": readings}).encode())
                body = json.loads(res["Payload"].read())
                if res.get("FunctionError") or "stored" not in body:
                    raise RuntimeError(f"function returned an error: {str(body)[:120]}")
                with self._lock:
                    self._s["telemetry_batches"] += 1
                    self._s["telemetry_readings"] += int(body["stored"])
                    self._s["telemetry_rejected"] += int(body.get("rejected", 0))
                self._ok()
            except Exception as e:
                self._fail("telemetry", e)

    def _loop(self) -> None:
        while not self._stop.wait(1.0):
            try:
                self.flush()
            except Exception as e:  # never let the worker die
                self._fail("worker", e)

    def stop(self) -> None:
        self._stop.set()
        try:
            self.flush(force=True)  # best-effort final send
        except Exception:
            pass

    def status(self) -> dict:
        with self._lock:
            return {"enabled": True, "region": self.region, "max_batches": self.max_batches,
                    "interval_s": self.interval_s, **self._s}
