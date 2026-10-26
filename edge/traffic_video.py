from ultralytics import YOLO
import cv2
import json
from datetime import datetime

# Load YOLO model
model = YOLO("yolov8n.pt")

# Vehicle classes
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

video_path = "data/traffic.mp4"

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open traffic video.")
    exit()

window_name = "Traffic Vehicle Detection"

cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 1280, 720)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # Run YOLO on original-quality frame
    results = model(frame, verbose=False)

    car_count = 0
    motorcycle_count = 0
    bus_count = 0
    truck_count = 0

    # Draw detection boxes on original frame
    for result in results:

        for box in result.boxes:

            class_id = int(box.cls[0])

            if class_id not in VEHICLE_CLASSES:
                continue

            vehicle_name = VEHICLE_CLASSES[class_id]

            # Count vehicles
            if vehicle_name == "car":
                car_count += 1

            elif vehicle_name == "motorcycle":
                motorcycle_count += 1

            elif vehicle_name == "bus":
                bus_count += 1

            elif vehicle_name == "truck":
                truck_count += 1

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

    # Total vehicles
    total_vehicles = (
        car_count
        + motorcycle_count
        + bus_count
        + truck_count
    )

    # Traffic density
    if total_vehicles <= 5:
        traffic_density = "LOW"

    elif total_vehicles <= 12:
        traffic_density = "MEDIUM"

    else:
        traffic_density = "HIGH"

    # Resize video BEFORE adding text
    display_frame = cv2.resize(
        frame,
        (1280, 720),
        interpolation=cv2.INTER_AREA
    )

    # Information panel
    cv2.rectangle(
        display_frame,
        (15, 15),
        (390, 225),
        (0, 0, 0),
        -1
    )

    # Header
    cv2.putText(
        display_frame,
        "TRAFFIC MONITORING",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    # Vehicle information
    cv2.putText(
        display_frame,
        f"Cars: {car_count}",
        (30, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        display_frame,
        f"Motorcycles: {motorcycle_count}",
        (30, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        display_frame,
        f"Buses: {bus_count}",
        (30, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        display_frame,
        f"Trucks: {truck_count}",
        (30, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        display_frame,
        f"Total Vehicles: {total_vehicles}",
        (30, 210),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2,
        cv2.LINE_AA
    )

    # Density indicator
    cv2.rectangle(
        display_frame,
        (950, 20),
        (1250, 80),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        display_frame,
        f"Density: {traffic_density}",
        (975, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2,
        cv2.LINE_AA
    )

    # Display
    cv2.imshow(window_name, display_frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()

# Save traffic data
traffic_data = {
    "location": "Intersection_01",
    "timestamp": datetime.now().isoformat(),
    "cars": car_count,
    "motorcycles": motorcycle_count,
    "buses": bus_count,
    "trucks": truck_count,
    "vehicle_count": total_vehicles,
    "traffic_density": traffic_density
}

with open("data/traffic_data.json", "w") as file:
    json.dump(traffic_data, file, indent=4)

print("\nTraffic analysis completed.")
print(json.dumps(traffic_data, indent=4))
print("\nData saved to data/traffic_data.json")