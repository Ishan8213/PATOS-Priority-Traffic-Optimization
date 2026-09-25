import json
import os
from datetime import datetime


# ==========================================
# PATOS Cloud Storage Simulation
# ==========================================

SOURCE_FILE = "data/traffic_data.json"

CLOUD_FOLDER = "data/cloud_storage"

OUTPUT_FILE = os.path.join(
    CLOUD_FOLDER,
    "traffic_telemetry.json"
)


# ==========================================
# Create cloud storage folder
# ==========================================

os.makedirs(
    CLOUD_FOLDER,
    exist_ok=True
)


# ==========================================
# Check source data
# ==========================================

if not os.path.exists(SOURCE_FILE):

    print("\nERROR: traffic_data.json not found.")

    print(
        "Run the YOLO tracking pipeline first."
    )

    exit()


# ==========================================
# Read edge telemetry
# ==========================================

with open(
    SOURCE_FILE,
    "r"
) as f:

    traffic_data = json.load(f)


# ==========================================
# Create cloud telemetry record
# ==========================================

cloud_record = {

    "device_id": "EdgeDevice01",

    "cloud_received_timestamp":
        datetime.now().isoformat(),

    "location":
        traffic_data.get(
            "location",
            "Intersection_01"
        ),

    "vehicle_count":
        traffic_data.get(
            "vehicle_count",
            0
        ),

    "cars":
        traffic_data.get(
            "cars",
            0
        ),

    "motorcycles":
        traffic_data.get(
            "motorcycles",
            0
        ),

    "buses":
        traffic_data.get(
            "buses",
            0
        ),

    "trucks":
        traffic_data.get(
            "trucks",
            0
        ),

    "traffic_density":
        traffic_data.get(
            "traffic_density",
            "UNKNOWN"
        )
}


# ==========================================
# Save cloud record
# ==========================================

with open(
    OUTPUT_FILE,
    "w"
) as f:

    json.dump(
        cloud_record,
        f,
        indent=4
    )


# ==========================================
# Display result
# ==========================================

print("\n==========================================")
print("PATOS - CLOUD STORAGE LAYER")
print("==========================================")

print("\nEdge telemetry received.")

print("\nCloud record:")

print(
    json.dumps(
        cloud_record,
        indent=4
    )
)

print(
    "\nCloud storage simulation saved to:"
)

print(
    OUTPUT_FILE
)

print("\n==========================================")