from ultralytics import YOLO

# Load YOLO model
model = YOLO("yolov8n.pt")

# Run detection on a sample image
results = model("https://ultralytics.com/images/bus.jpg")

# Display results
for result in results:
    result.show()

print("YOLO vehicle detection test completed.")