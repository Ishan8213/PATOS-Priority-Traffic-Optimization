"""OPTIONAL edge component: count unique vehicles in a video with YOLOv8 tracking and send the
summary to the local server (or any endpoint that accepts the same JSON).

Needs the extra packages in requirements-video.txt (PyTorch is large). The local demo and its
tests do not need this file.

  python edge/video_counter.py --video path/to/traffic.mp4 --intersection N_2_2

NOTE: the count is the number of unique tracker IDs seen so far (cars, motorcycles, buses,
trucks), not an instantaneous density. It has not been validated against ground truth.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

COCO_VEHICLES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def update_tracks(seen: dict, ids, classes) -> dict:
    """Record (track id -> vehicle type) for the detections in one frame."""
    if ids is None:
        return seen
    for tid, cls in zip(ids, classes):
        label = COCO_VEHICLES.get(int(cls))
        if label is not None:
            seen[int(tid)] = label
    return seen


def summarize(seen: dict) -> dict:
    counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    for label in seen.values():
        counts[label] += 1
    return {"total": len(seen), **counts}


def post_telemetry(url: str, intersection_id: str, count: int, timeout: float = 5.0) -> dict:
    body = json.dumps({"intersection_id": intersection_id, "vehicle_count": int(count)}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"stored": False, "http_status": e.code, "detail": e.read().decode("utf-8", "replace")[:200]}


def run(video: str, model_path: str, intersection_id: str, url: str, every_frames: int) -> None:
    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("ultralytics is not installed. Run: pip install -r requirements-video.txt")
    model = YOLO(model_path)  # 'yolov8n.pt' is downloaded automatically on first use
    seen: dict = {}
    frame = 0
    for result in model.track(source=video, stream=True, persist=True, classes=list(COCO_VEHICLES),
                              verbose=False, show=False):
        frame += 1
        boxes = result.boxes
        if boxes is not None and boxes.id is not None:
            update_tracks(seen, boxes.id.int().tolist(), boxes.cls.int().tolist())
        if frame % every_frames == 0:
            print(f"frame {frame}: {summarize(seen)}", post_telemetry(url, intersection_id, len(seen)))
    summary = summarize(seen)
    print("final:", summary, post_telemetry(url, intersection_id, summary["total"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--intersection", required=True, help="a signalized node id, e.g. N_2_2")
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--url", default="http://127.0.0.1:8000/api/telemetry")
    ap.add_argument("--every-frames", type=int, default=150)
    a = ap.parse_args()
    run(a.video, a.model, a.intersection, a.url, a.every_frames)
