import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from edge.runtime_config import display_video_enabled, project_path


MODEL_PATH = project_path("PATOS_YOLO_MODEL_PATH", "yolov8n.pt")
VIDEO_PATH = project_path("PATOS_VIDEO_PATH", "data/traffic.mp4")
OUTPUT_PATH = project_path("PATOS_TRAFFIC_OUTPUT_PATH", "data/traffic_data.json")
WINDOW_NAME = "PATOS - YOLO Vehicle Tracking"
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


def draw_text(image, text, position, scale, color, thickness=2):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (width, height), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = position

    cv2.rectangle(
        image,
        (x - 5, y - height - 7),
        (x + width + 5, y + baseline + 7),
        (0, 0, 0),
        -1,
    )
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        scale,
        color,
        thickness,
        cv2.LINE_8,
    )


def main():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"YOLO model was not found: {MODEL_PATH}")
    if not VIDEO_PATH.is_file():
        raise FileNotFoundError(f"Traffic video was not found: {VIDEO_PATH}")

    show_video = display_video_enabled()
    model = YOLO(str(MODEL_PATH))
    capture = cv2.VideoCapture(str(VIDEO_PATH))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open traffic video: {VIDEO_PATH}")

    vehicle_ids = {name: set() for name in VEHICLE_CLASSES.values()}
    all_vehicle_ids = set()
    stop_requested = False

    try:
        if show_video:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 1280, 720)

        while not stop_requested:
            success, frame = capture.read()
            if not success:
                break

            frame = cv2.resize(
                frame,
                (1280, 720),
                interpolation=cv2.INTER_LINEAR,
            )
            results = model.track(
                frame,
                persist=True,
                classes=list(VEHICLE_CLASSES),
                verbose=False,
            )
            annotated_frame = frame.copy()

            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    if box.id is None:
                        continue

                    track_id = int(box.id[0])
                    class_id = int(box.cls[0])
                    vehicle_type = VEHICLE_CLASSES.get(class_id)
                    if vehicle_type is None:
                        continue

                    vehicle_ids[vehicle_type].add(track_id)
                    all_vehicle_ids.add(track_id)
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(
                        annotated_frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2,
                    )
                    draw_text(
                        annotated_frame,
                        f"{vehicle_type} ID:{track_id}",
                        (x1, max(y1 - 10, 30)),
                        0.75,
                        (0, 255, 0),
                    )

            cars = len(vehicle_ids["car"])
            motorcycles = len(vehicle_ids["motorcycle"])
            buses = len(vehicle_ids["bus"])
            trucks = len(vehicle_ids["truck"])
            total_vehicles = len(all_vehicle_ids)
            if total_vehicles < 10:
                traffic_density = "LOW"
            elif total_vehicles < 25:
                traffic_density = "MEDIUM"
            else:
                traffic_density = "HIGH"

            if show_video:
                draw_text(
                    annotated_frame,
                    f"Unique Vehicles: {total_vehicles}",
                    (20, 45),
                    0.9,
                    (255, 255, 255),
                )
                draw_text(
                    annotated_frame,
                    f"Cars: {cars}  Motorcycles: {motorcycles}",
                    (20, 85),
                    0.8,
                    (255, 255, 255),
                )
                draw_text(
                    annotated_frame,
                    f"Buses: {buses}  Trucks: {trucks}",
                    (20, 125),
                    0.8,
                    (255, 255, 255),
                )
                draw_text(
                    annotated_frame,
                    f"Traffic Density: {traffic_density}",
                    (20, 170),
                    0.9,
                    (0, 255, 255),
                )
                cv2.imshow(WINDOW_NAME, annotated_frame)
                stop_requested = cv2.waitKey(1) & 0xFF == ord("q")
    finally:
        capture.release()
        if show_video:
            cv2.destroyAllWindows()

    cars = len(vehicle_ids["car"])
    motorcycles = len(vehicle_ids["motorcycle"])
    buses = len(vehicle_ids["bus"])
    trucks = len(vehicle_ids["truck"])
    total_vehicles = len(all_vehicle_ids)
    if total_vehicles < 10:
        traffic_density = "LOW"
    elif total_vehicles < 25:
        traffic_density = "MEDIUM"
    else:
        traffic_density = "HIGH"

    traffic_data = {
        "location": "Intersection_01",
        "timestamp": datetime.now().isoformat(),
        "cars": cars,
        "motorcycles": motorcycles,
        "buses": buses,
        "trucks": trucks,
        "vehicle_count": total_vehicles,
        "traffic_density": traffic_density,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(traffic_data, output_file, indent=4)

    print("\n====================================")
    print("YOLO VEHICLE TRACKING COMPLETED")
    print("====================================")
    print("Unique Vehicles:", total_vehicles)
    print("Cars:", cars)
    print("Motorcycles:", motorcycles)
    print("Buses:", buses)
    print("Trucks:", trucks)
    print("Traffic Density:", traffic_density)
    print(f"\nTracking data saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
