import os
from pathlib import Path


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# AWS actions are disabled until these values are explicitly configured.
S3_BUCKET = os.getenv("PATOS_S3_BUCKET", "")
S3_OBJECT_KEY = os.getenv(
    "PATOS_S3_OBJECT_KEY",
    "traffic/traffic_telemetry.json"
)

IOT_ENDPOINT = os.getenv("PATOS_IOT_ENDPOINT", "")
IOT_TOPIC = os.getenv("PATOS_IOT_TOPIC", "patos/traffic/telemetry")
DEVICE_ID = os.getenv("PATOS_DEVICE_ID", "EdgeDevice01")
IOT_CERTIFICATE = os.getenv("PATOS_IOT_CERTIFICATE", "")
IOT_PRIVATE_KEY = os.getenv("PATOS_IOT_PRIVATE_KEY", "")
IOT_ROOT_CA = os.getenv(
    "PATOS_IOT_ROOT_CA",
    str(Path("certs") / "AmazonRootCA1.pem")
)