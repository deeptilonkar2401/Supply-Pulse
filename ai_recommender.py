import anthropic, json, os, random
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# ❌ REMOVE GLOBAL CLIENT (important fix)

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
    route   = shipment["route_stops"]
    origin  = shipment["origin"]
    dest    = shipment["destination"]
    blocked = shipment["current_location"]

    alt1_stops = [city for city in route if city != blocked]
    if origin not in alt1_stops:
        alt1_stops.insert(0, origin)
    if dest not in alt1_stops:
        alt1_stops.append(dest)

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
Routes:
1. Current: {' > '.join(routes['original']['stops'])}
2. Alt 1: {' > '.join(routes['alternate_1']['stops'])}
3. Alt 2: {' > '.join(routes['alternate_2']['stops'])}
"""

    try:
        # ✅ CREATE CLIENT HERE (not global)
        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role":"user","content":prompt}]
        )

        recommendation = msg.content[0].text

    except Exception as e:
        # ✅ fallback (no crash)
        recommendation = (
            f"HIGH RISK at {shipment['current_location']}. "
            f"Use alternate route to avoid delay. "
            f"Prioritize delivery of {shipment['cargo_type']}."
        )

    return {
        "recommendation": recommendation,
        "routes": routes,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
