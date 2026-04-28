import anthropic, json, os, random
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY","your-key-here"))

CITIES = {
    "Mumbai":{"lat":19.0760,"lon":72.8777},"Delhi":{"lat":28.6139,"lon":77.2090},
    "Kolkata":{"lat":22.5726,"lon":88.3639},"Chennai":{"lat":13.0827,"lon":80.2707},
    "Bangalore":{"lat":12.9716,"lon":77.5946},"Hyderabad":{"lat":17.3850,"lon":78.4867},
    "Pune":{"lat":18.5204,"lon":73.8567},"Ahmedabad":{"lat":23.0225,"lon":72.5714},
    "Jaipur":{"lat":26.9124,"lon":75.7873},"Nagpur":{"lat":21.1458,"lon":79.0882},
    "Lucknow":{"lat":26.8467,"lon":80.9462},"Bhopal":{"lat":23.2599,"lon":77.4126},
    "Surat":{"lat":21.1702,"lon":72.8311},"Indore":{"lat":22.7196,"lon":75.8577},
    "Raipur":{"lat":21.2514,"lon":81.6296},
}

def build_alternate_routes(shipment):
    """
    Build alternate routes keeping correct order — origin to destination.
    Alt1: Skip the currently BLOCKED city, keep rest in order
    Alt2: Direct origin to destination
    """
    route   = shipment["route_stops"]   # e.g. [Mumbai, Pune, Hyderabad, Chennai, Bangalore]
    origin  = shipment["origin"]        # Mumbai
    dest    = shipment["destination"]   # Bangalore
    blocked = shipment["current_location"]  # e.g. Pune (the problem city)

    # Alt 1: Remove ONLY the blocked city, preserve order of rest
    # e.g. [Mumbai, Hyderabad, Chennai, Bangalore] — Pune skipped
    alt1_stops = [city for city in route if city != blocked]
    # Make sure origin and destination are still there
    if origin not in alt1_stops:
        alt1_stops.insert(0, origin)
    if dest not in alt1_stops:
        alt1_stops.append(dest)

    # Alt 2: Direct route — current location straight to destination
    # e.g. truck is at Pune, go directly Pune → Bangalore
    current = shipment["current_location"]
    alt2_stops = [current, dest]

    return {
        "original": {
            "stops": route,
            "estimated_hrs": len(route) * 6,
            "extra_cost_inr": 0
        },
        "alternate_1": {
            "stops": alt1_stops,
            "estimated_hrs": len(alt1_stops) * 6 + 2,
            "extra_cost_inr": random.randint(2000, 6000),
            "description": f"Skip {blocked}, continue to {dest}"
        },
        "alternate_2": {
            "stops": alt2_stops,
            "estimated_hrs": len(alt2_stops) * 5 + 1,
            "extra_cost_inr": random.randint(4000, 10000),
            "description": f"Direct from {current} to {dest}"
        },
    }

def get_ai_recommendation(shipment):
    routes = build_alternate_routes(shipment)
    prompt = f"""You are a logistics expert AI for India supply chain.
Shipment {shipment['shipment_id']} is HIGH RISK. Give a SHORT 3-line recommendation.
Cargo: {shipment['cargo_type']} (sensitivity: {shipment['sensitivity']})
Current Location: {shipment['current_location']} | Destination: {shipment['destination']}
Risk Score: {shipment['risk_score']}/100
Weather Risk: {shipment.get('weather_score','N/A')} | Traffic: {shipment.get('traffic_score','N/A')}
Routes:
1. Current: {' > '.join(routes['original']['stops'])} | {routes['original']['estimated_hrs']}h | Rs.0
2. Alt 1 (skip blocked): {' > '.join(routes['alternate_1']['stops'])} | {routes['alternate_1']['estimated_hrs']}h | Rs.{routes['alternate_1']['extra_cost_inr']}
3. Alt 2 (direct): {' > '.join(routes['alternate_2']['stops'])} | {routes['alternate_2']['estimated_hrs']}h | Rs.{routes['alternate_2']['extra_cost_inr']}
State: main risk, best route, hours saved. Be direct and practical."""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role":"user","content":prompt}]
        )
        recommendation = msg.content[0].text
    except Exception as e:
        recommendation = (
            f"HIGH RISK at {shipment['current_location']} due to weather+traffic. "
            f"Recommend Alt Route 1 — skip {shipment['current_location']} and continue to {shipment['destination']}. "
            f"Estimated 2-3h delay avoided. Critical for {shipment['cargo_type']} cargo."
        )

    return {
        "recommendation": recommendation,
        "routes": routes,
        "delay_avoided_hrs": round(
            abs(routes['alternate_1']['estimated_hrs'] - routes['original']['estimated_hrs']) * 0.6, 1
        ),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
