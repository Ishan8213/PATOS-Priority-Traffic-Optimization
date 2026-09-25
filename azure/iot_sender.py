import json
import os
import time

try:
    from azure.iot.device import IoTHubDeviceClient, Message
except ImportError:
    print("Azure IoT SDK is not installed.")
    print("Run:")
    print("pip install azure-iot-device")
    exit()


# ==========================================
# Configuration
# ==========================================

from config import (
    IOT_HUB_CONNECTION_STRING,
    DEVICE_ID,
    TELEMETRY_INTERVAL
)


DATA_FILE = "data/traffic_data.json"


# ==========================================
# Check Azure configuration
# ==========================================

if not IOT_HUB_CONNECTION_STRING:

    print("\n==========================================")
    print("AZURE IOT HUB CONFIGURATION")
    print("==========================================")

    print("\nAzure IoT Hub connection string is not configured.")

    print(
        "\nThe local PATOS system is working correctly."
    )

    print(
        "Azure transmission will be enabled when "
        "an active IoT Hub device is available."
    )

    print("\nCurrent Device ID:", DEVICE_ID)

    print("\nNo data has been sent to Azure.")

    print("==========================================")

    exit()


# ==========================================
# Load traffic data
# ==========================================

if not os.path.exists(DATA_FILE):

    print(
        f"\nERROR: {DATA_FILE} was not found."
    )

    print(
        "Run the YOLO tracking pipeline first."
    )

    exit()


with open(DATA_FILE, "r") as f:

    traffic_data = json.load(f)


# ==========================================
# Add edge-device information
# ==========================================

telemetry = {

    "device_id": DEVICE_ID,

    "location": traffic_data.get(
        "location",
        "Intersection_01"
    ),

    "timestamp": traffic_data.get(
        "timestamp"
    ),

    "cars": traffic_data.get(
        "cars",
        0
    ),

    "motorcycles": traffic_data.get(
        "motorcycles",
        0
    ),

    "buses": traffic_data.get(
        "buses",
        0
    ),

    "trucks": traffic_data.get(
        "trucks",
        0
    ),

    "vehicle_count": traffic_data.get(
        "vehicle_count",
        0
    ),

    "traffic_density": traffic_data.get(
        "traffic_density",
        "UNKNOWN"
    )
}


# ==========================================
# Convert to JSON
# ==========================================

message_body = json.dumps(
    telemetry
)


message = Message(
    message_body
)

message.content_type = "application/json"
message.content_encoding = "utf-8"


# ==========================================
# Connect to Azure IoT Hub
# ==========================================

print("\n==========================================")
print("PATOS - AZURE IOT HUB TELEMETRY")
print("==========================================")

print("\nDevice:", DEVICE_ID)

print("Connecting to Azure IoT Hub...")


try:

    client = IoTHubDeviceClient.create_from_connection_string(
        IOT_HUB_CONNECTION_STRING
    )

    client.connect()

    print("Connected successfully.")

    print("\nSending telemetry:")

    print(
        json.dumps(
            telemetry,
            indent=4
        )
    )


    # ======================================
    # Send telemetry
    # ======================================

    client.send_message(message)

    print("\nTelemetry sent successfully.")


    # ======================================
    # Disconnect
    # ======================================

    client.disconnect()

    print("Disconnected from Azure IoT Hub.")

    print("\n==========================================")


except Exception as e:

    print("\nAzure IoT Hub connection failed.")

    print("Error:", e)

    print(
        "\nCheck the IoT Hub connection string "
        "and device configuration."
    )