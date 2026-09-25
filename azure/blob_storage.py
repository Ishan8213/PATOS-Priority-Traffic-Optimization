import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRAFFIC_FILE = os.path.join(
    BASE_DIR,
    "data",
    "traffic_data.json"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "blob_storage"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_json(path):
    with open(path, "r") as file:
        return json.load(file)


traffic = load_json(TRAFFIC_FILE)

blob_object = {
    "blob_name": "traffic_telemetry.json",
    "uploaded_at": datetime.now().isoformat(),
    "source_device": "EdgeDevice01",
    "location": traffic.get(
        "location",
        "Intersection_01"
    ),
    "vehicle_count": traffic.get(
        "vehicle_count",
        0
    ),
    "cars": traffic.get(
        "cars",
        0
    ),
    "motorcycles": traffic.get(
        "motorcycles",
        0
    ),
    "buses": traffic.get(
        "buses",
        0
    ),
    "trucks": traffic.get(
        "trucks",
        0
    ),
    "traffic_density": traffic.get(
        "traffic_density",
        "LOW"
    )
}


output_file = os.path.join(
    OUTPUT_DIR,
    "traffic_telemetry.json"
)

with open(output_file, "w") as file:
    json.dump(blob_object, file, indent=4)


print("Blob Storage preparation completed.")
print(f"Blob-ready file created at: {output_file}")