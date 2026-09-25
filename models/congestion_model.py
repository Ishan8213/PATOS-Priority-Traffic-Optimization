import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# -----------------------------------------
# Create sample traffic dataset
# -----------------------------------------

np.random.seed(42)

data = []

for i in range(1000):

    vehicle_count = np.random.randint(1, 101)

    avg_speed = np.random.randint(10, 61)

    occupancy = np.random.uniform(0.05, 1.0)

    # Create congestion label
    if vehicle_count > 70 or occupancy > 0.75 or avg_speed < 20:
        congestion = "HIGH"

    elif vehicle_count > 40 or occupancy > 0.45 or avg_speed < 35:
        congestion = "MEDIUM"

    else:
        congestion = "LOW"

    data.append([
        vehicle_count,
        avg_speed,
        occupancy,
        congestion
    ])


df = pd.DataFrame(
    data,
    columns=[
        "vehicle_count",
        "avg_speed",
        "occupancy",
        "congestion"
    ]
)


# -----------------------------------------
# Features and target
# -----------------------------------------

X = df[
    [
        "vehicle_count",
        "avg_speed",
        "occupancy"
    ]
]

y = df["congestion"]


# -----------------------------------------
# Train/test split
# -----------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# -----------------------------------------
# Train Random Forest
# -----------------------------------------

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)


# -----------------------------------------
# Evaluate
# -----------------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n===================================")
print(" CONGESTION PREDICTION MODEL")
print("===================================")

print(f"\nModel Accuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions
    )
)


# -----------------------------------------
# Save model
# -----------------------------------------

joblib.dump(
    model,
    "models/congestion_model.pkl"
)

print("\nModel saved to:")
print("models/congestion_model.pkl")