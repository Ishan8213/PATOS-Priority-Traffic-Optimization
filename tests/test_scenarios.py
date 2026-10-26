import json
import os


# ==========================================
# Helper functions
# ==========================================

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)


def run_scenario(name, traffic_density, predicted_congestion,
                 priority_level, priority_action,
                 signal_action, green_time, red_time):

    result = {
        "scenario": name,
        "traffic_density": traffic_density,
        "predicted_congestion": predicted_congestion,
        "priority_level": priority_level,
        "priority_action": priority_action,
        "signal_action": signal_action,
        "green_time": green_time,
        "red_time": red_time
    }

    return result


# ==========================================
# Scenario 1 - Normal Traffic
# ==========================================

scenario_1 = run_scenario(
    name="Normal Traffic",
    traffic_density="LOW",
    predicted_congestion="LOW",
    priority_level="NORMAL",
    priority_action="NORMAL_OPERATION",
    signal_action="NORMAL_OPERATION",
    green_time=30,
    red_time=30
)


# ==========================================
# Scenario 2 - High Congestion
# ==========================================

scenario_2 = run_scenario(
    name="High Congestion",
    traffic_density="HIGH",
    predicted_congestion="HIGH",
    priority_level="NORMAL",
    priority_action="NORMAL_OPERATION",
    signal_action="HIGH_CONGESTION_OPTIMIZATION",
    green_time=60,
    red_time=30
)


# ==========================================
# Scenario 3 - Critical Ambulance
# ==========================================

scenario_3 = run_scenario(
    name="Critical Ambulance Priority",
    traffic_density="MEDIUM",
    predicted_congestion="MEDIUM",
    priority_level="CRITICAL",
    priority_action="IMMEDIATE_SIGNAL_PRIORITY",
    signal_action="GREEN_PRIORITY",
    green_time=60,
    red_time=15
)


# ==========================================
# Store all scenarios
# ==========================================

results = [
    scenario_1,
    scenario_2,
    scenario_3
]


os.makedirs("data", exist_ok=True)

save_json(
    "data/test_scenarios.json",
    results
)


# ==========================================
# Display results
# ==========================================

print("\n")
print("=" * 75)
print("PATOS - SCENARIO TEST RESULTS")
print("=" * 75)

for result in results:

    print("\nScenario:", result["scenario"])

    print(
        "Traffic Density:",
        result["traffic_density"]
    )

    print(
        "Predicted Congestion:",
        result["predicted_congestion"]
    )

    print(
        "Priority Level:",
        result["priority_level"]
    )

    print(
        "Priority Action:",
        result["priority_action"]
    )

    print(
        "Signal Action:",
        result["signal_action"]
    )

    print(
        "Green Time:",
        result["green_time"],
        "seconds"
    )

    print(
        "Red Time:",
        result["red_time"],
        "seconds"
    )

    print("-" * 75)


print("\nAll scenarios completed successfully.")

print(
    "\nResults saved to:"
    " data/test_scenarios.json"
)