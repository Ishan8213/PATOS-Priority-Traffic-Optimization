import json
import os
import ssl

from config import (
    DEVICE_ID,
    IOT_CERTIFICATE,
    IOT_ENDPOINT,
    IOT_PRIVATE_KEY,
    IOT_ROOT_CA,
    IOT_TOPIC,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "traffic_data.json")
certificate = (
    os.path.abspath(os.path.join(BASE_DIR, IOT_CERTIFICATE))
    if IOT_CERTIFICATE
    else ""
)
private_key = (
    os.path.abspath(os.path.join(BASE_DIR, IOT_PRIVATE_KEY))
    if IOT_PRIVATE_KEY
    else ""
)
root_ca = os.path.abspath(os.path.join(BASE_DIR, IOT_ROOT_CA))

if not IOT_ENDPOINT or not certificate or not private_key:
    print("AWS IoT Core publishing skipped: set PATOS_IOT_ENDPOINT,")
    print("PATOS_IOT_CERTIFICATE and PATOS_IOT_PRIVATE_KEY to opt in.")
    raise SystemExit(0)

missing_files = [
    path for path in (certificate, private_key, root_ca)
    if not os.path.isfile(path)
]
if missing_files:
    raise FileNotFoundError(
        "AWS IoT Core certificate file(s) not found: "
        + ", ".join(missing_files)
    )

if not os.path.isfile(DATA_FILE):
    raise FileNotFoundError(
        f"{DATA_FILE} was not found. Run the traffic pipeline first."
    )

try:
    import paho.mqtt.client as mqtt
except ImportError as error:
    raise RuntimeError(
        "AWS IoT Core publishing requires paho-mqtt. "
        "Install it with: pip install paho-mqtt"
    ) from error

with open(DATA_FILE, "r", encoding="utf-8") as file:
    telemetry = json.load(file)

telemetry["device_id"] = DEVICE_ID
payload = json.dumps(telemetry)

client = mqtt.Client(client_id=DEVICE_ID, clean_session=True)
client.tls_set(
    ca_certs=root_ca,
    certfile=certificate,
    keyfile=private_key,
    tls_version=ssl.PROTOCOL_TLS_CLIENT,
)

print(f"Publishing traffic telemetry to AWS IoT Core topic {IOT_TOPIC!r}...")
client.connect(IOT_ENDPOINT, port=8883, keepalive=60)
client.loop_start()
try:
    publish_result = client.publish(IOT_TOPIC, payload, qos=1)
    publish_result.wait_for_publish(timeout=10)
    if not publish_result.is_published():
        raise TimeoutError("AWS IoT Core telemetry publish timed out.")
finally:
    client.loop_stop()
    client.disconnect()

print("AWS IoT Core telemetry published successfully.")
