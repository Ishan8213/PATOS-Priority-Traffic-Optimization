import streamlit as st
import json
import os

st.set_page_config(
    page_title="PATOS - Traffic Optimization",
    page_icon="🚦",
    layout="wide"
)


def load_json(filename):
    path = os.path.join("data", filename)

    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Load data
traffic = load_json("traffic_data.json")
congestion = load_json("congestion_prediction.json")
priority = load_json("priority_decision.json")
signal = load_json("signal_optimization.json")


# =================================================
# HEADER
# =================================================

st.title("PATOS")
st.subheader(
    "Priority-Aware Traffic Optimization System"
)

st.write(
    "Edge–Cloud framework for intelligent traffic monitoring, "
    "congestion prediction and priority-aware traffic signal optimization."
)

st.divider()


# =================================================
# SYSTEM STATUS
# =================================================

st.header("System Status")

priority_action = priority.get(
    "priority_action",
    "NORMAL_OPERATION"
)

if priority_action == "IMMEDIATE_SIGNAL_PRIORITY":

    st.success(
        "CRITICAL PRIORITY MODE — GREEN CORRIDOR ACTIVE"
    )

elif priority_action == "SIGNAL_PRIORITY":

    st.warning(
        "PRIORITY VEHICLE MODE ACTIVE"
    )

else:

    st.info(
        "NORMAL TRAFFIC OPERATION"
    )


# =================================================
# TRAFFIC MONITORING
# =================================================

st.header("Real-Time Traffic Monitoring")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Vehicles",
        traffic.get("vehicle_count", "N/A")
    )

with col2:
    st.metric(
        "Cars",
        traffic.get("cars", "N/A")
    )

with col3:
    st.metric(
        "Motorcycles",
        traffic.get("motorcycles", "N/A")
    )

with col4:
    st.metric(
        "Traffic Density",
        traffic.get("traffic_density", "N/A")
    )


# =================================================
# CONGESTION
# =================================================

st.divider()

st.header("AI Congestion Prediction")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Predicted Congestion",
        congestion.get(
            "predicted_congestion",
            "N/A"
        )
    )

with col2:
    st.metric(
        "Average Speed",
        congestion.get(
            "avg_speed",
            "N/A"
        )
    )

with col3:
    st.metric(
        "Road Occupancy",
        congestion.get(
            "occupancy",
            "N/A"
        )
    )


# =================================================
# PRIORITY VEHICLE
# =================================================

st.divider()

st.header("Priority Vehicle Management")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Vehicle ID**")
    st.write(
        priority.get(
            "vehicle_id",
            "NONE"
        )
    )

with col2:
    st.write("**Vehicle Type**")
    st.write(
        priority.get(
            "vehicle_type",
            "NONE"
        )
    )

with col3:
    st.write("**Priority Level**")
    st.write(
        priority.get(
            "priority_level",
            "NORMAL"
        )
    )


if priority_action == "IMMEDIATE_SIGNAL_PRIORITY":

    st.success(
        "Authorized critical vehicle detected — "
        "signal priority activated."
    )

elif priority_action == "SIGNAL_PRIORITY":

    st.warning(
        "Priority vehicle detected — "
        "extended signal timing activated."
    )

else:

    st.info(
        "No active priority vehicle."
    )


# =================================================
# ROUTE
# =================================================

if priority.get("signal_recommendations"):

    st.subheader("Priority Route")

    for recommendation in priority["signal_recommendations"]:

        st.write(
            f"Intersection: "
            f"**{recommendation.get('intersection', 'N/A')}** "
            f"→ "
            f"**{recommendation.get('action', 'N/A')}**"
        )


# =================================================
# SIGNAL OPTIMIZATION
# =================================================

st.divider()

st.header("Adaptive Signal Optimization")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Signal Action",
        signal.get(
            "signal_action",
            "N/A"
        )
    )

with col2:
    st.metric(
        "Green Time",
        f'{signal.get("recommended_green_time", "N/A")} sec'
    )

with col3:
    st.metric(
        "Red Time",
        f'{signal.get("recommended_red_time", "N/A")} sec'
    )

with col4:
    st.metric(
        "Intersection",
        signal.get(
            "location",
            "N/A"
        )
    )


# =================================================
# FINAL DECISION
# =================================================

st.divider()

st.header("Final System Decision")

st.info(
    f"""
**Intersection:** {signal.get("location", "N/A")}

**Traffic Density:** {traffic.get("traffic_density", "N/A")}

**Predicted Congestion:** {congestion.get("predicted_congestion", "N/A")}

**Priority Action:** {priority.get("priority_action", "N/A")}

**Signal Action:** {signal.get("signal_action", "N/A")}

**Recommended Green:** {signal.get("recommended_green_time", "N/A")} seconds

**Recommended Red:** {signal.get("recommended_red_time", "N/A")} seconds
"""
)


# =================================================
# FOOTER
# =================================================

st.divider()

st.caption(
    "PATOS | Priority-Aware Edge–Cloud Framework "
    "for Intelligent Traffic Signal Optimization"
)