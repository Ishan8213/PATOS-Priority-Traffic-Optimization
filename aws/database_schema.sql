CREATE TABLE TrafficRecords (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id VARCHAR(100),
    location VARCHAR(100),
    timestamp TIMESTAMPTZ,
    vehicle_count INTEGER,
    cars INTEGER,
    motorcycles INTEGER,
    buses INTEGER,
    trucks INTEGER,
    traffic_density VARCHAR(20)
);


CREATE TABLE CongestionPredictions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location VARCHAR(100),
    prediction_time TIMESTAMPTZ,
    predicted_congestion VARCHAR(20),
    vehicle_count INTEGER,
    average_speed FLOAT,
    occupancy FLOAT
);


CREATE TABLE PriorityEvents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id VARCHAR(100),
    vehicle_type VARCHAR(50),
    priority_level VARCHAR(30),
    current_location VARCHAR(100),
    destination VARCHAR(100),
    authorized BOOLEAN,
    priority_action VARCHAR(100),
    event_time TIMESTAMPTZ
);


CREATE TABLE SignalRecommendations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location VARCHAR(100),
    recommendation_time TIMESTAMPTZ,
    signal_action VARCHAR(100),
    green_time INTEGER,
    red_time INTEGER,
    predicted_congestion VARCHAR(20),
    priority_action VARCHAR(100)
);