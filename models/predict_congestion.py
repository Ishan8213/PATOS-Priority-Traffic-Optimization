import joblib
import json


# Load trained model
model = joblib.load(
    "models/congestion_model.pkl"
)


# Load current traffic data
with open(
    "data/traffic_data.json",
    "r"
) as file:

    traffic_data = json.load(file)


# -----------------------------------------
# Prepare current traffic information
# -----------------------------------------

vehicle_count = traffic_data["vehicle_count"]


# Prototype values
# These will later come from real traffic
# measurements.

avg_speed = 30
occupancy = 0.55


# -----------------------------------------
# Predict congestion
# -----------------------------------------

prediction = model.predict([
    [
        vehicle_count,
        avg_speed,
        occupancy
    ]
])[0]


# -----------------------------------------
# Save prediction
# -----------------------------------------

result = {

    "location":
        traffic_data["location"],

    "vehicle_count":
        vehicle_count,

    "average_speed":
        avg_speed,

    "occupancy":
        occupancy,

    "predicted_congestion":
        prediction
}


with open(
    "data/congestion_prediction.json",
    "w"
) as file:

    json.dump(
        result,
        file,
        indent=4
    )


# -----------------------------------------
# Display
# -----------------------------------------

print("\n===================================")
print(" CONGESTION PREDICTION")
print("===================================")

print(
    f"\nVehicle Count : {vehicle_count}"
)

print(
    f"Average Speed: {avg_speed} km/h"
)

print(
    f"Occupancy    : {occupancy}"
)

print(
    f"\nPredicted Congestion: {prediction}"
)

print(
    "\nPrediction saved to:"
)

print(
    "data/congestion_prediction.json"
)