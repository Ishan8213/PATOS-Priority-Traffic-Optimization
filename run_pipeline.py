import os
import subprocess
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(name, command):
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, *command)],
        check=True,
        cwd=BASE_DIR
    )

    return result.returncode


steps = [
    (
        "1. EDGE VEHICLE TRACKING",
        ["edge/traffic_tracking.py"]
    ),
    (
        "2. CONGESTION PREDICTION",
        ["models/predict_congestion.py"]
    ),
    (
        "3. PRIORITY MANAGEMENT",
        ["priority/priority_manager.py"]
    ),
    (
        "4. SIGNAL OPTIMIZATION",
        ["optimization/signal_optimizer.py"]
    ),
    (
        "5. SQL DATA PREPARATION",
        ["aws/prepare_sql_data.py"]
    ),
    (
        "6. SQL INSERT GENERATION",
        ["aws/generate_sql_inserts.py"]
    ),
    (
        "7. AWS S3 STORAGE",
        ["aws/s3_storage.py"]
    ),
    (
        "8. AWS IOT CORE TELEMETRY",
        ["aws/iot_sender.py"]
    )
]


print("\nPATOS - COMPLETE PIPELINE")
print("Priority-Aware Traffic Optimization System")


for name, command in steps:
    run_step(name, command)


print("\n" + "=" * 60)
print("PATOS PIPELINE COMPLETED SUCCESSFULLY")
print("=" * 60)

print("\nGenerated outputs:")

outputs = [
    "data/traffic_data.json",
    "data/congestion_prediction.json",
    "data/priority_decision.json",
    "data/signal_optimization.json",
    "data/sql_ready/sql_ready_data.json",
    "data/sql_ready/insert_data.sql",
    "data/aws_storage/traffic_telemetry.json"
]

for output in outputs:
    print(f"✓ {os.path.join(BASE_DIR, output)}")