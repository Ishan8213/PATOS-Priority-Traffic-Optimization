from ultralytics import YOLO
import cv2
import json
from datetime import datetime


model = YOLO("yolov8n.pt")

video_path = "data/traffic.mp4"

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("ERROR: Could not open traffic video.")
    exit()


vehicle_classes = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


unique_vehicle_ids = set()
car_ids = set()
motorcycle_ids = set()
bus_ids = set()
truck_ids = set()


cv2.namedWindow(
    "PATOS - YOLO Vehicle Tracking",
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    "PATOS - YOLO Vehicle Tracking",
    1280,
    720
)


# ==========================================
# Clean text with black background
# ==========================================

def draw_text(
    image,
    text,
    position,
    scale,
    color,
    thickness=2
):

    font = cv2.FONT_HERSHEY_SIMPLEX

    (w, h), baseline = cv2.getTextSize(
        text,
        font,
        scale,
        thickness
    )

    x, y = position

    # Black background
    cv2.rectangle(
        image,
        (x - 5, y - h - 7),
        (x + w + 5, y + baseline + 7),
        (0, 0, 0),
        -1
    )

    # Sharp text
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        scale,
        color,
        thickness,
        cv2.LINE_8
    )


# ==========================================
# Process video
# ==========================================

while True:

    success, frame = cap.read()

    if not success:
        break


    # ======================================
    # Resize FIRST
    # ======================================

    frame = cv2.resize(
        frame,
        (1280, 720),
        interpolation=cv2.INTER_LINEAR
    )


    # ======================================
    # YOLO tracking
    # ======================================

    results = model.track(
        frame,
        persist=True,
        classes=list(vehicle_classes.keys()),
        verbose=False
    )


    annotated_frame = frame.copy()


    # ======================================
    # Process vehicles
    # ======================================

    for result in results:

        if result.boxes is None:
            continue


        for box in result.boxes:

            if box.id is None:
                continue


            track_id = int(box.id[0])
            class_id = int(box.cls[0])


            if class_id not in vehicle_classes:
                continue


            vehicle_type = vehicle_classes[class_id]


            unique_vehicle_ids.add(track_id)


            if vehicle_type == "car":
                car_ids.add(track_id)

            elif vehicle_type == "motorcycle":
                motorcycle_ids.add(track_id)

            elif vehicle_type == "bus":
                bus_ids.add(track_id)

            elif vehicle_type == "truck":
                truck_ids.add(track_id)


            # Bounding box
            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )


            # Green bounding box
            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )


            # Vehicle label
            label = f"{vehicle_type} ID:{track_id}"


            draw_text(
                annotated_frame,
                label,
                (x1, max(y1 - 10, 30)),
                0.75,
                (0, 255, 0),
                2
            )


    # ======================================
    # Statistics
    # ======================================

    total_unique = len(unique_vehicle_ids)

    cars = len(car_ids)
    motorcycles = len(motorcycle_ids)
    buses = len(bus_ids)
    trucks = len(truck_ids)


    if total_unique < 10:
        traffic_density = "LOW"

    elif total_unique < 25:
        traffic_density = "MEDIUM"

    else:
        traffic_density = "HIGH"


    # ======================================
    # Clean statistics text
    # ======================================

    draw_text(
        annotated_frame,
        f"Unique Vehicles: {total_unique}",
        (20, 45),
        0.9,
        (255, 255, 255),
        2
    )


    draw_text(
        annotated_frame,
        f"Cars: {cars}  Motorcycles: {motorcycles}",
        (20, 85),
        0.8,
        (255, 255, 255),
        2
    )


    draw_text(
        annotated_frame,
        f"Buses: {buses}  Trucks: {trucks}",
        (20, 125),
        0.8,
        (255, 255, 255),
        2
    )


    draw_text(
        annotated_frame,
        f"Traffic Density: {traffic_density}",
        (20, 170),
        0.9,
        (0, 255, 255),
        2
    )


    # ======================================
    # Display
    # ======================================

    cv2.imshow(
        "PATOS - YOLO Vehicle Tracking",
        annotated_frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# Cleanup
# ==========================================

cap.release()
cv2.destroyAllWindows()


# ==========================================
# Save results
# ==========================================

traffic_data = {
    "location": "Intersection_01",
    "timestamp": datetime.now().isoformat(),
    "cars": cars,
    "motorcycles": motorcycles,
    "buses": buses,
    "trucks": trucks,
    "vehicle_count": total_unique,
    "traffic_density": traffic_density
}


with open(
    "data/traffic_data.json",
    "w"
) as f:

    json.dump(
        traffic_data,
        f,
        indent=4
    )


print("\n====================================")
print("YOLO VEHICLE TRACKING COMPLETED")
print("====================================")
print("Unique Vehicles:", total_unique)
print("Cars:", cars)
print("Motorcycles:", motorcycles)
print("Buses:", buses)
print("Trucks:", trucks)
print("Traffic Density:", traffic_density)
print("\nTracking data saved successfully.")