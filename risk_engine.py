import json
import random
from datetime import datetime
from mock_data import get_risk_level, CITIES

def calculate_weather_score(location):
    """
    Simulate weather risk score for a location.
    In real project: call OpenWeather API here.
    Returns score 0-100
    """
    # Simulated weather conditions
    weather_events = {
        "Mumbai":    random.randint(20, 90),
        "Delhi":     random.randint(10, 70),
        "Kolkata":   random.randint(30, 95),
        "Chennai":   random.randint(25, 85),
        "Bangalore": random.randint(10, 60),
        "Hyderabad": random.randint(15, 75),
        "Pune":      random.randint(20, 80),
        "Ahmedabad": random.randint(10, 65),
        "Jaipur":    random.randint(5,  60),
        "Nagpur":    random.randint(20, 85),
        "Lucknow":   random.randint(15, 70),
        "Bhopal":    random.randint(20, 75),
        "Surat":     random.randint(25, 80),
        "Indore":    random.randint(15, 70),
        "Raipur":    random.randint(25, 85),
    }
    return weather_events.get(location, random.randint(20, 70))


def calculate_traffic_score(location):
    """
    Simulate traffic congestion score for a location.
    In real project: call Google Maps API here.
    Returns score 0-100
    """
    traffic_data = {
        "Mumbai":    random.randint(50, 95),
        "Delhi":     random.randint(55, 95),
        "Kolkata":   random.randint(40, 90),
        "Chennai":   random.randint(35, 85),
        "Bangalore": random.randint(50, 95),
        "Hyderabad": random.randint(30, 80),
        "Pune":      random.randint(35, 85),
        "Ahmedabad": random.randint(25, 75),
        "Jaipur":    random.randint(20, 65),
        "Nagpur":    random.randint(20, 70),
        "Lucknow":   random.randint(30, 75),
        "Bhopal":    random.randint(20, 65),
        "Surat":     random.randint(35, 80),
        "Indore":    random.randint(25, 70),
        "Raipur":    random.randint(15, 60),
    }
    return traffic_data.get(location, random.randint(20, 70))


def calculate_historical_delay_score(route_stops):
    """
    Simulate historical delay rate for a route.
    In real project: query your database for past delay records.
    Returns score 0-100
    """
    # Routes with more cities = historically more delays
    base_score = len(route_stops) * 8
    noise      = random.randint(-15, 25)
    return min(100, max(0, base_score + noise))


def calculate_risk_score(shipment):
    """
    MAIN RISK SCORING FUNCTION
    4-factor weighted formula:
      Weather severity    -> 35%
      Traffic congestion  -> 30%
      Historical delay    -> 20%
      Cargo sensitivity   -> 15%
    """
    current_loc = shipment["current_location"]
    route_stops = shipment["route_stops"]
    multiplier  = shipment["risk_multiplier"]

    # Get individual scores
    weather_score   = calculate_weather_score(current_loc)
    traffic_score   = calculate_traffic_score(current_loc)
    historical_score= calculate_historical_delay_score(route_stops)

    # Cargo sensitivity base score
    sensitivity_map = {"critical": 80, "high": 60, "medium": 40, "low": 20}
    cargo_score     = sensitivity_map.get(shipment["sensitivity"], 40)

    # Weighted composite score
    raw_score = (
        weather_score    * 0.35 +
        traffic_score    * 0.30 +
        historical_score * 0.20 +
        cargo_score      * 0.15
    )

    # Apply cargo risk multiplier
    final_score = min(100, round(raw_score * multiplier))

    return {
        "final_score":       final_score,
        "weather_score":     weather_score,
        "traffic_score":     traffic_score,
        "historical_score":  historical_score,
        "cargo_score":       cargo_score,
    }


def find_cascade_shipments(affected_location, all_shipments, current_id):
    """
    CASCADE PROPAGATION ENGINE
    Find all shipments that pass through the same location
    as the high-risk shipment — flag them too.
    """
    cascade_ids = []
    for s in all_shipments:
        if s["shipment_id"] == current_id:
            continue
        if affected_location in s["route_stops"]:
            cascade_ids.append(s["shipment_id"])
    return cascade_ids


def run_risk_engine():
    """
    Run full risk recalculation on all shipments.
    This function is called every 60 seconds by the scheduler.
    """
    try:
        with open("shipments.json", "r") as f:
            shipments = json.load(f)
    except FileNotFoundError:
        print("shipments.json not found. Run mock_data.py first.")
        return []

    cascade_warnings = {}

    for shipment in shipments:
        # Skip already rerouted shipments
        if shipment["rerouted"]:
            continue

        # Calculate new risk score
        scores = calculate_risk_score(shipment)
        shipment["risk_score"]      = scores["final_score"]
        shipment["weather_score"]   = scores["weather_score"]
        shipment["traffic_score"]   = scores["traffic_score"]
        shipment["historical_score"]= scores["historical_score"]
        shipment["cargo_score"]     = scores["cargo_score"]
        shipment["risk_level"]      = get_risk_level(
            scores["final_score"], shipment["sensitivity"]
        )

        # If HIGH risk -> find cascade shipments
        if shipment["risk_level"] == "high":
            cascade_ids = find_cascade_shipments(
                shipment["current_location"], shipments, shipment["shipment_id"]
            )
            if cascade_ids:
                cascade_warnings[shipment["shipment_id"]] = {
                    "location":     shipment["current_location"],
                    "cascade_ids":  cascade_ids,
                    "count":        len(cascade_ids)
                }

    # Save updated shipments
    with open("shipments.json", "w") as f:
        json.dump(shipments, f, indent=2)

    # Summary
    high   = sum(1 for s in shipments if s["risk_level"] == "high")
    medium = sum(1 for s in shipments if s["risk_level"] == "medium")
    low    = sum(1 for s in shipments if s["risk_level"] == "low")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Risk engine ran -> "
          f"HIGH: {high} | MEDIUM: {medium} | LOW: {low} | "
          f"Cascades detected: {len(cascade_warnings)}")

    return shipments, cascade_warnings


if __name__ == "__main__":
    print("Running risk engine manually...")
    shipments, cascades = run_risk_engine()
    print(f"\nCascade warnings: {len(cascades)}")
    for sid, info in cascades.items():
        print(f"  {sid} at {info['location']} -> affects {info['count']} other shipments")
