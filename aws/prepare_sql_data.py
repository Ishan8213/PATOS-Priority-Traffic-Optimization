import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRAFFIC_FILE = os.path.join(BASE_DIR, "data", "traffic_data.json")
CONGESTION_FILE = os.path.join(BASE_DIR, "data", "congestion_prediction.json")
PRIORITY_FILE = os.path.join(BASE_DIR, "data", "priority_decision.json")
SIGNAL_FILE = os.path.join(BASE_DIR, "data", "signal_optimization.json")

OUTPUT_DIR = os.path.join(BASE_DIR, "data", "sql_ready")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_json(path):
    with open(path, "r") as file:
        return json.load(file)


# Load pipeline outputs
traffic = load_json(TRAFFIC_FILE)
congestion = load_json(CONGESTION_FILE)
priority = load_json(PRIORITY_FILE)
signal = load_json(SIGNAL_FILE)

timestamp = datetime.now().isoformat()


# ---------------------------------------------------
# 1. Traffic Record
# ---------------------------------------------------

traffic_record = {
    "device_id": "EdgeDevice01",
    "location": traffic.get("location", "Intersection_01"),
    "timestamp": timestamp,
    "vehicle_count": traffic.get("vehicle_count", 0),
    "cars": traffic.get("cars", 0),
    "motorcycles": traffic.get("motorcycles", 0),
    "buses": traffic.get("buses", 0),
    "trucks": traffic.get("trucks", 0),
    "traffic_density": traffic.get("traffic_density", "LOW")
}


# ---------------------------------------------------
# 2. Congestion Prediction
# ---------------------------------------------------

congestion_record = {
    "location": traffic.get("location", "Intersection_01"),
    "prediction_time": timestamp,
    "predicted_congestion": congestion.get(
        "predicted_congestion",
        "UNKNOWN"
    ),
    "vehicle_count": traffic.get("vehicle_count", 0),
    "average_speed": congestion.get("average_speed", 30),
    "occupancy": congestion.get("occupancy", 0.55)
}


# ---------------------------------------------------
# 3. Priority Event
# ---------------------------------------------------

priority_record = {
    "vehicle_id": priority.get("vehicle_id", ""),
    "vehicle_type": priority.get("vehicle_type", ""),
    "priority_level": priority.get("priority_level", "NORMAL"),
    "current_location": priority.get(
        "current_location",
        "Intersection_01"
    ),
    "destination": priority.get("destination", ""),
    "authorized": priority.get("authorized", False),
    "priority_action": priority.get(
        "priority_action",
        "NORMAL_OPERATION"
    ),
    "event_time": timestamp
}


# ---------------------------------------------------
# 4. Signal Recommendation
# ---------------------------------------------------

signal_record = {
    "location": signal.get(
        "location",
        traffic.get("location", "Intersection_01")
    ),
    "recommendation_time": timestamp,
    "signal_action": signal.get(
        "signal_action",
        "NORMAL_OPERATION"
    ),
    "green_time": signal.get(
        "green_time",
        signal.get("recommended_green_time", 30)
    ),
    "red_time": signal.get(
        "red_time",
        signal.get("recommended_red_time", 30)
    ),
    "predicted_congestion": congestion.get(
        "predicted_congestion",
        "UNKNOWN"
    ),
    "priority_action": priority.get(
        "priority_action",
        "NORMAL_OPERATION"
    )
}


# ---------------------------------------------------
# Save SQL-ready JSON files
# ---------------------------------------------------

records = {
    "traffic_record": traffic_record,
    "congestion_record": congestion_record,
    "priority_record": priority_record,
    "signal_record": signal_record
}

output_file = os.path.join(
    OUTPUT_DIR,
    "sql_ready_data.json"
)

with open(output_file, "w") as file:
    json.dump(records, file, indent=4)


print("PostgreSQL-compatible SQL data preparation completed (local only).")
print(f"SQL-ready data saved to: {output_file}")

print("\nTraffic Record:")
print(traffic_record)

print("\nCongestion Record:")
print(congestion_record)

print("\nPriority Record:")
print(priority_record)

print("\nSignal Recommendation:")
print(signal_record)