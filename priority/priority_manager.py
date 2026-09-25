import json

# Load traffic data
with open("data/traffic_data.json", "r") as f:
    traffic = json.load(f)

# Load priority request
with open("priority/priority_request.json", "r") as f:
    request = json.load(f)


traffic_density = traffic["traffic_density"]
priority_level = request["priority_level"]
authorized = request["authorized"]


# --------------------------------
# Priority Decision
# --------------------------------

if authorized and priority_level == "CRITICAL":

    priority_action = "IMMEDIATE_SIGNAL_PRIORITY"

elif authorized and priority_level == "HIGH":

    priority_action = "SIGNAL_PRIORITY"

else:

    priority_action = "NORMAL_OPERATION"


# --------------------------------
# Create Decision
# --------------------------------

decision = {
    "location": traffic["location"],
    "traffic_density": traffic_density,
    "vehicle_id": request["vehicle_id"],
    "vehicle_type": request["vehicle_type"],
    "priority_level": priority_level,
    "authorized": authorized,
    "priority_action": priority_action,
    "signal_recommendations": []
}


# Add route recommendations if priority vehicle exists
if authorized and request["route"]:

    for intersection in request["route"]:

        decision["signal_recommendations"].append({
            "intersection": intersection,
            "action": "GREEN_PRIORITY"
        })


# Save decision
with open("data/priority_decision.json", "w") as f:
    json.dump(decision, f, indent=4)


print("\n===== PRIORITY MANAGEMENT =====")
print("Vehicle:", request["vehicle_id"])
print("Vehicle Type:", request["vehicle_type"])
print("Priority Level:", priority_level)
print("Authorized:", authorized)
print("Priority Action:", priority_action)
print("===============================")

print("\nPriority decision saved successfully.")