# PATOS – signal-aware routing (local first, AWS later)

Pick an origin and destination on a live map and get the **fastest route** plus **alternates**, each
with a **signal-by-signal plan**: the predicted red/green phase when you arrive, the legal wait, and the
ETA. An **emergency_operator** also gets **advisory priority requests**; every request is **audited**.
You can animate the trip and watch the vehicle stop at reds.

> Demonstration only. Sensors are simulated, signal timing is a modeled fixed-time plan, and the road
> network is a synthetic 6×6 grid. Nothing controls a real signal and nothing here tells a driver to
> disregard one. This local version needs **no AWS account** and installs **no third-party packages**
> to run (pytest only for tests).

## Run it in VS Code (Windows, macOS or Linux)

1. Install **Python 3.10+** (on Windows tick "Add python.exe to PATH") and **VS Code** with the *Python* extension.
2. VS Code: **File → Open Folder…** and choose this `patos-aws` folder.
3. Open a terminal (**Terminal → New Terminal**) and run:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
   python -m pip install -r requirements-dev.txt
   python -m pytest                    # all tests should pass
   python run_local.py                 # opens http://127.0.0.1:8000
   ```

   If PowerShell blocks the activate script, run
   `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.
   Or press **F5** and pick **PATOS local demo**.

## Using the demo

- Click a node for the origin (**A**), another for the destination (**B**), then **Find routes**.
- Cards show each route's ETA split into driving time and signal waiting. Click a card to select it;
  the table lists every signal on it (arrival, phase on arrival, wait).
- **Animate selected trip** plays the journey (1×–20×). Signals are shown at the simulated time, so you
  can see the vehicle wait at a red and leave on green.
- Choose vehicle **AMBULANCE / FIRE_TRUCK / POLICE** with role **emergency_operator** to see advisory
  priority requests and the ETA if they were granted. With role **driver** the request is routed as an
  ordinary vehicle and marked denied. (The role selector is a local stand-in for Cognito groups, not security.)
- **Pause sensors** and wait 5 minutes to watch telemetry go stale; **Traffic load** changes congestion.
- Cross at each signal: vertical bar = north–south, horizontal bar = east–west. Ring = congestion.

Optional: `python scripts/benchmark.py` reruns the signal-aware vs signal-ignorant experiment.
Optional real video counting: `pip install -r requirements-video.txt`, then
`python edge/video_counter.py --video your.mp4 --intersection N_2_2` (needs the demo running; large
PyTorch download; **untested** in this project's verification).

## How the local demo maps to AWS (for the later deployment)

| Local | AWS version (see `docs/DEPLOY.md`) |
|---|---|
| Sensor simulator thread | AWS IoT Core topic `patos/telemetry/<id>` |
| `handlers/ingest.py` via `/api/telemetry` | IoT rule → Lambda |
| In-memory telemetry table | Amazon DynamoDB (with TTL) |
| `handlers/route.py` via `/api/route` | API Gateway + Lambda |
| Role selector | Amazon Cognito groups |
| In-memory audit table | DynamoDB audit table |

The routing, signal and priority code in `src/patos/` and the two handlers are **identical** in both
versions; only the storage and the front door change. Deploy only when you are ready: nothing in the
local demo touches AWS.

## Optional: mirror to AWS (hybrid mode, Lambda + DynamoDB only)

`python run_local.py --aws PatosHybridDemo` keeps everything running locally and also writes each audit
record to DynamoDB and sends sensor readings to a Lambda function. It is best-effort: if AWS fails,
the local app carries on. Setup, evidence checklist and a full **teardown** checklist are in
`docs/HYBRID_DEPLOY.md`. Do not enable IAM Identity Center on a Free plan account.

## Layout

`run_local.py` entry · `local/` server + web UI · `src/patos/` core logic · `src/handlers/` Lambda-style
handlers · `simulator/` sensor simulator · `edge/` optional video counter · `tests/` · `local/aws_sync.py` + `infra/hybrid_stack.py` hybrid AWS mode, `infra/patos_stack.py`, `client/`,
`docs/` AWS deployment (optional) · `scripts/` graph generator and benchmark.

## Verification status

| Verified (Linux sandbox) | Not verified |
|---|---|
| 95 automated tests pass (82 without AWS tools, plus 13 infrastructure checks that need `requirements-aws.txt`); AWS calls are tested only against fake clients; both CDK stacks synthesise; real local server answered route requests; web page exercised in a simulated DOM with no script errors | Anything against a real AWS account (deployment, the `--aws` mode, whether `cdk` accepts `aws login` credentials, cost); running on Windows; viewing the page in a real browser; the optional YOLO video counter |

## Known limits

Synthetic grid; fixed-time two-phase signals only (no turn, pedestrian or adaptive phases); congestion
multipliers (1.0 / 1.3 / 1.8 by vehicle count) are uncalibrated; priority is advisory; the local server
binds to 127.0.0.1 and has no real authentication.
