import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "sql_ready",
    "sql_ready_data.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "sql_ready",
    "insert_data.sql"
)


def sql_string(value):
    if value is None:
        return "NULL"

    value = str(value).replace("'", "''")
    return f"'{value}'"


with open(INPUT_FILE, "r") as file:
    data = json.load(file)


traffic = data["traffic_record"]
congestion = data["congestion_record"]
priority = data["priority_record"]
signal = data["signal_record"]


sql = f"""
-- PATOS Azure SQL Data Inserts

INSERT INTO TrafficRecords
(device_id, location, timestamp, vehicle_count, cars,
 motorcycles, buses, trucks, traffic_density)
VALUES
(
    {sql_string(traffic["device_id"])},
    {sql_string(traffic["location"])},
    {sql_string(traffic["timestamp"])},
    {traffic["vehicle_count"]},
    {traffic["cars"]},
    {traffic["motorcycles"]},
    {traffic["buses"]},
    {traffic["trucks"]},
    {sql_string(traffic["traffic_density"])}
);


INSERT INTO CongestionPredictions
(location, prediction_time, predicted_congestion,
 vehicle_count, average_speed, occupancy)
VALUES
(
    {sql_string(congestion["location"])},
    {sql_string(congestion["prediction_time"])},
    {sql_string(congestion["predicted_congestion"])},
    {congestion["vehicle_count"]},
    {congestion["average_speed"]},
    {congestion["occupancy"]}
);


INSERT INTO PriorityEvents
(vehicle_id, vehicle_type, priority_level,
 current_location, destination, authorized,
 priority_action, event_time)
VALUES
(
    {sql_string(priority["vehicle_id"])},
    {sql_string(priority["vehicle_type"])},
    {sql_string(priority["priority_level"])},
    {sql_string(priority["current_location"])},
    {sql_string(priority["destination"])},
    {1 if priority["authorized"] else 0},
    {sql_string(priority["priority_action"])},
    {sql_string(priority["event_time"])}
);


INSERT INTO SignalRecommendations
(location, recommendation_time, signal_action,
 green_time, red_time, predicted_congestion,
 priority_action)
VALUES
(
    {sql_string(signal["location"])},
    {sql_string(signal["recommendation_time"])},
    {sql_string(signal["signal_action"])},
    {signal["green_time"]},
    {signal["red_time"]},
    {sql_string(signal["predicted_congestion"])},
    {sql_string(signal["priority_action"])}
);
"""


with open(OUTPUT_FILE, "w") as file:
    file.write(sql.strip())


print("SQL INSERT generation completed.")
print(f"SQL file created at: {OUTPUT_FILE}")