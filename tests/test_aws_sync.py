import io
import json
import threading
import time
import urllib.request
from decimal import Decimal

import pytest

from handlers import ingest, ingest_batch
from local.aws_sync import AwsSync, outputs_of
from local.server import create_server
from tests.test_handlers import FakeTable


class FakeLambda:
    def __init__(self, fail=False, response=None):
        self.calls, self.fail, self.response = [], fail, response

    def invoke(self, FunctionName, InvocationType, Payload):
        if self.fail:
            raise RuntimeError("AccessDenied: not allowed")
        self.calls.append((FunctionName, json.loads(Payload)))
        body = self.response or {"stored": len(json.loads(Payload)["readings"]), "rejected": 0}
        return {"Payload": io.BytesIO(json.dumps(body).encode())}


class FlakyTable(FakeTable):
    def __init__(self, failures):
        super().__init__()
        self.failures = failures

    def put_item(self, Item):
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("throttled")
        super().put_item(Item)


def make(**kw):
    audit, lam = kw.pop("audit", FakeTable()), kw.pop("lam", FakeLambda())
    return AwsSync(audit, lam, "fn-name", autostart=False, region="test-1", **kw), audit, lam


TEL = {"intersection_id": "N_2_2", "vehicle_count": Decimal(12), "cycle_start_ts": Decimal("1800000000.5")}


def test_audit_records_are_written():
    sync, audit, _ = make()
    sync.enqueue_audit({"request_id": "r1", "ts": 1})
    sync.flush()
    assert "r1" in audit.items and sync.status()["audit_sent"] == 1


def test_audit_retries_then_gives_up_without_raising():
    sync, audit, _ = make(audit=FlakyTable(failures=2))
    sync.enqueue_audit({"request_id": "r1"})
    for _ in range(3):
        sync.flush()
    assert "r1" in audit.items and sync.status()["audit_failed"] == 0
    sync2, _, _ = make(audit=FlakyTable(failures=99))
    sync2.enqueue_audit({"request_id": "r2"})
    for _ in range(5):
        sync2.flush()
    st = sync2.status()
    assert st["audit_failed"] == 1 and "throttled" in st["last_error"]


def test_telemetry_is_batched_latest_only_and_rate_limited():
    sync, _, lam = make(interval_s=3600)
    sync.note_telemetry({**TEL, "vehicle_count": 5})
    sync.note_telemetry(TEL)                                     # same intersection: latest wins
    sync.note_telemetry({"intersection_id": "N_3_3", "vehicle_count": 7})
    sync.flush()
    assert len(lam.calls) == 1
    fn, payload = lam.calls[0]
    assert fn == "fn-name" and {r["intersection_id"]: r["vehicle_count"] for r in payload["readings"]} == {"N_2_2": 12, "N_3_3": 7}
    sync.note_telemetry(TEL)
    sync.flush()                                                  # too soon: nothing sent
    assert len(lam.calls) == 1
    sync.flush(force=True)
    assert len(lam.calls) == 2 and sync.status()["telemetry_batches"] == 2


def test_batch_limit_pauses_uploads():
    sync, _, lam = make(interval_s=0, max_batches=2)
    for _ in range(4):
        sync.note_telemetry(TEL)
        sync.flush(force=True)
    st = sync.status()
    assert len(lam.calls) == 2 and st["paused"] is True and st["telemetry_batches"] == 2


def test_aws_failure_is_reported_not_raised():
    sync, _, _ = make(lam=FakeLambda(fail=True))
    sync.note_telemetry(TEL)
    sync.flush(force=True)
    st = sync.status()
    assert st["telemetry_batches"] == 0 and "AccessDenied" in st["last_error"]


def test_function_error_is_detected():
    sync, _, _ = make(lam=FakeLambda(response={"errorMessage": "boom"}))
    sync.note_telemetry(TEL)
    sync.flush(force=True)
    assert "function returned an error" in sync.status()["last_error"]


def test_outputs_of_checks_status_and_keys():
    class Cfn:
        def __init__(self, status, outputs):
            self.s = {"Stacks": [{"StackStatus": status, "Outputs": outputs}]}

        def describe_stacks(self, StackName):
            return self.s
    good = [{"OutputKey": "AuditTableName", "OutputValue": "a"}, {"OutputKey": "IngestFunctionName", "OutputValue": "f"}]
    assert outputs_of(Cfn("CREATE_COMPLETE", good), "S") == {"AuditTableName": "a", "IngestFunctionName": "f"}
    with pytest.raises(RuntimeError, match="ROLLBACK"):
        outputs_of(Cfn("ROLLBACK_COMPLETE", good), "S")
    with pytest.raises(RuntimeError, match="hybrid stack"):
        outputs_of(Cfn("CREATE_COMPLETE", []), "S")


# ---- cloud-side Lambda handler ----
@pytest.fixture
def tel_table(monkeypatch):
    t = FakeTable()
    monkeypatch.setattr(ingest, "_get_table", lambda: t)
    return t


def test_ingest_batch_stores_valid_and_rejects_invalid(tel_table):
    now = time.time()
    out = ingest_batch.handler({"readings": [
        {"intersection_id": "N_1_1", "vehicle_count": 4, "cycle_start_ts": now - 10},
        {"intersection_id": "N_0_0", "vehicle_count": 4},        # not signalized
        {"intersection_id": "N_2_2", "vehicle_count": -3},       # bad count
        "oops",
    ]}, None)
    assert out == {"stored": 1, "rejected": 3} and list(tel_table.items) == ["N_1_1"]


@pytest.mark.parametrize("event", [{}, {"readings": []}, {"readings": "x"}, None])
def test_ingest_batch_rejects_malformed_events(tel_table, event):
    assert ingest_batch.handler(event, None)["stored"] == 0


def test_ingest_batch_enforces_size_limit(tel_table):
    out = ingest_batch.handler({"readings": [{"intersection_id": "N_1_1", "vehicle_count": 1}] * 51}, None)
    assert out["stored"] == 0 and "at most" in out["reason"] and tel_table.items == {}


# ---- local server wired to AWS sync ----
def test_server_mirrors_audit_and_reports_status():
    sync, audit, lam = make(interval_s=0)
    httpd, engine = create_server(port=0, simulate=False, interval_s=3600, aws=sync)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        body = json.dumps({"origin": {"node_id": "N_0_0"}, "destination": {"node_id": "N_5_5"}, "vehicle_type": "CAR"}).encode()
        req = urllib.request.Request(base + "/api/route", data=body, headers={"Content-Type": "application/json"})
        assert json.loads(urllib.request.urlopen(req).read())["fastest"]["eta_s"] > 0
        sync.flush(force=True)
        assert len(audit.items) == 1                                   # audit record reached "AWS"
        assert lam.calls and lam.calls[0][1]["readings"]               # initial sensor round was uploaded
        st = json.loads(urllib.request.urlopen(base + "/api/state").read())["aws"]
        assert st["enabled"] and st["audit_sent"] == 1 and st["region"] == "test-1"
    finally:
        httpd.shutdown()
        engine.stop()
        httpd.server_close()


def test_local_app_survives_aws_outage():
    sync, audit, _ = make(audit=FlakyTable(failures=99), lam=FakeLambda(fail=True))
    httpd, engine = create_server(port=0, simulate=False, interval_s=3600, aws=sync)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        body = json.dumps({"origin": {"node_id": "N_0_0"}, "destination": {"node_id": "N_5_5"}, "vehicle_type": "CAR"}).encode()
        req = urllib.request.Request(base + "/api/route", data=body, headers={"Content-Type": "application/json"})
        assert urllib.request.urlopen(req).status == 200
        sync.flush(force=True)
        assert json.loads(urllib.request.urlopen(base + "/api/state").read())["aws"]["last_error"]
    finally:
        httpd.shutdown()
        engine.stop()
        httpd.server_close()
