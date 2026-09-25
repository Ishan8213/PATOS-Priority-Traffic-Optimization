import json

# Load traffic data
with open("data/traffic_data.json", "r") as f:
    traffic = json.load(f)

# Load congestion prediction
with open("data/congestion_prediction.json", "r") as f:
    congestion = json.load(f)

# Load priority decision
with open("data/priority_decision.json", "r") as f:
    priority = json.load(f)


# Extract information
traffic_density = traffic["traffic_density"]
predicted_congestion = congestion["predicted_congestion"]
priority_action = priority["priority_action"]


# ---------------------------------
# Priority-aware signal optimization
# ---------------------------------

if priority_action == "IMMEDIATE_SIGNAL_PRIORITY":

    green_time = 60
    red_time = 15
    signal_action = "GREEN_PRIORITY"

elif priority_action == "SIGNAL_PRIORITY":

    green_time = 50
    red_time = 25
    signal_action = "EXTENDED_GREEN"

else:

    if predicted_congestion == "HIGH":
        green_time = 60
        red_time = 30
        signal_action = "HIGH_CONGESTION_OPTIMIZATION"

    elif predicted_congestion == "MEDIUM":
        green_time = 45
        red_time = 45
        signal_action = "MEDIUM_CONGESTION_OPTIMIZATION"

    else:
        green_time = 30
        red_time = 30
        signal_action = "NORMAL_OPERATION"


# Final result
result = {
    "location": traffic["location"],
    "traffic_density": traffic_density,
    "predicted_congestion": predicted_congestion,
    "priority_action": priority_action,
    "signal_action": signal_action,
    "recommended_green_time": green_time,
    "recommended_red_time": red_time
}


# Save final optimization result
with open("data/signal_optimization.json", "w") as f:
    json.dump(result, f, indent=4)


# Display result
print("\n===== SIGNAL OPTIMIZATION RESULT =====")
print("Location:", result["location"])
print("Traffic Density:", result["traffic_density"])
print("Predicted Congestion:", result["predicted_congestion"])
print("Priority Action:", result["priority_action"])
print("Signal Action:", result["signal_action"])
print("Recommended Green Time:", green_time, "seconds")
print("Recommended Red Time:", red_time, "seconds")
print("======================================")

print("\nSignal optimization saved successfully.")