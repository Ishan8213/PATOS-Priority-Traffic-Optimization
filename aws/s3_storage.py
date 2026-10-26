import json
import os
from datetime import datetime

from config import AWS_REGION, S3_BUCKET, S3_OBJECT_KEY

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRAFFIC_FILE = os.path.join(
    BASE_DIR,
    "data",
    "traffic_data.json"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "aws_storage"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_json(path):
    with open(path, "r") as file:
        return json.load(file)


traffic = load_json(TRAFFIC_FILE)

blob_object = {
    "object_key": S3_OBJECT_KEY,
    "uploaded_at": datetime.now().isoformat(),
    "source_device": os.getenv("PATOS_DEVICE_ID", "EdgeDevice01"),
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

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(blob_object, file, indent=4)


print("AWS S3 telemetry file prepared.")
print(f"Local telemetry file: {output_file}")

if not S3_BUCKET:
    print("S3 upload skipped: set PATOS_S3_BUCKET to opt in.")
else:
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError(
            "S3 upload requires boto3. Install it with: pip install boto3"
        ) from error

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.upload_file(output_file, S3_BUCKET, S3_OBJECT_KEY)
    print(f"Uploaded to s3://{S3_BUCKET}/{S3_OBJECT_KEY}")