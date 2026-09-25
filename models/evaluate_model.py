import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# ==========================================
# Generate prototype traffic dataset
# ==========================================

np.random.seed(42)

n_samples = 1000

vehicle_count = np.random.randint(
    1, 101, n_samples
)

avg_speed = np.random.uniform(
    5, 60, n_samples
)

occupancy = np.random.uniform(
    0.05, 0.95, n_samples
)


# ==========================================
# Generate labels
# ==========================================

labels = []

for vehicles, speed, occ in zip(
    vehicle_count,
    avg_speed,
    occupancy
):

    if vehicles >= 70 or speed < 20 or occ > 0.75:

        labels.append("HIGH")

    elif vehicles >= 35 or speed < 40 or occ > 0.45:

        labels.append("MEDIUM")

    else:

        labels.append("LOW")


# ==========================================
# Create DataFrame
# ==========================================

data = pd.DataFrame({
    "vehicle_count": vehicle_count,
    "avg_speed": avg_speed,
    "occupancy": occupancy,
    "congestion": labels
})


# ==========================================
# Features and target
# ==========================================

X = data[
    [
        "vehicle_count",
        "avg_speed",
        "occupancy"
    ]
]

y = data["congestion"]


# ==========================================
# Train/test split
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# ==========================================
# Train model
# ==========================================

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(
    X_train,
    y_train
)


# ==========================================
# Predictions
# ==========================================

y_pred = model.predict(X_test)


# ==========================================
# Evaluation
# ==========================================

accuracy = accuracy_score(
    y_test,
    y_pred
)

print("\n======================================")
print("CONGESTION MODEL EVALUATION")
print("======================================")

print(
    f"\nAccuracy: {accuracy * 100:.2f}%"
)


print("\nClassification Report:")
print(
    classification_report(
        y_test,
        y_pred
    )
)


print("\nConfusion Matrix:")
print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


print("\n======================================")