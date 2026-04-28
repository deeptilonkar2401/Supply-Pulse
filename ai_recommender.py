import anthropic, os, random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CITIES = {
    "Mumbai":{"lat":19.0760,"lon":72.8777},
    "Delhi":{"lat":28.6139,"lon":77.2090},
    "Kolkata":{"lat":22.5726,"lon":88.3639},
    "Chennai":{"lat":13.0827,"lon":80.2707},
    "Bangalore":{"lat":12.9716,"lon":77.5946},
    "Hyderabad":{"lat":17.3850,"lon":78.4867},
    "Pune":{"lat":18.5204,"lon":73.8567},
    "Indore":{"lat":22.7196,"lon":75.8577},
}

def build_alternate_routes(shipment):
    route = shipment["route_stops"]
    origin = shipment["origin"]
    dest = shipment["destination"]
    blocked = shipment["current_location"]

    alt1 = [c for c in route if c != blocked]
    if origin not in alt1:
        alt1.insert(0, origin)
    if dest not in alt1:
        alt1.append(dest)

    alt2 = [blocked, dest]

    def coords(path):
        return [
            {"lat": CITIES[c]["lat"], "lon": CITIES[c]["lon"], "city": c}
            for c in path if c in CITIES
        ]

    return {
        "original": {
            "stops": route,
            "coords": coords(route),
            "hours": len(route) * 6
        },
        "alt1": {
            "stops": alt1,
            "coords": coords(alt1),
            "hours": len(alt1) * 6 + 2
        },
        "alt2": {
            "stops": alt2,
            "coords": coords(alt2),
            "hours": len(alt2) * 5 + 1
        }
    }


def get_ai_recommendation(shipment):
    routes = build_alternate_routes(shipment)

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    prompt = f"""
You are logistics AI.

Give short recommendation.

Risk: {shipment['risk_score']}
From {shipment['current_location']} to {shipment['destination']}

Routes:
1. {routes['original']['stops']}
2. {routes['alt1']['stops']}
3. {routes['alt2']['stops']}
"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role":"user","content":prompt}]
        )
        text = msg.content[0].text
    except:
        text = "Use alternate route for safety."

    return {
        "recommendation": text,
        "routes": routes
    }
