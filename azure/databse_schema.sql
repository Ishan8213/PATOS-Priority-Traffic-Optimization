CREATE TABLE TrafficRecords (
    id INT IDENTITY(1,1) PRIMARY KEY,
    device_id VARCHAR(100),
    location VARCHAR(100),
    timestamp DATETIME2,
    vehicle_count INT,
    cars INT,
    motorcycles INT,
    buses INT,
    trucks INT,
    traffic_density VARCHAR(20)
);


CREATE TABLE CongestionPredictions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    location VARCHAR(100),
    prediction_time DATETIME2,
    predicted_congestion VARCHAR(20),
    vehicle_count INT,
    average_speed FLOAT,
    occupancy FLOAT
);


CREATE TABLE PriorityEvents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    vehicle_id VARCHAR(100),
    vehicle_type VARCHAR(50),
    priority_level VARCHAR(30),
    current_location VARCHAR(100),
    destination VARCHAR(100),
    authorized BIT,
    priority_action VARCHAR(100),
    event_time DATETIME2
);


CREATE TABLE SignalRecommendations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    location VARCHAR(100),
    recommendation_time DATETIME2,
    signal_action VARCHAR(100),
    green_time INT,
    red_time INT,
    predicted_congestion VARCHAR(20),
    priority_action VARCHAR(100)
);