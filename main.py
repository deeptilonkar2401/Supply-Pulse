from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json, os, random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from mock_data import generate_all_shipments, CITIES
from risk_engine import run_risk_engine
from ai_recommender import get_ai_recommendation, build_alternate_routes

app = FastAPI(title="SupplyPulse")

# Ensure data file exists
if not os.path.exists("shipments.json"):
    generate_all_shipments(200)

audit_trail = []

# ---------------- HOME ----------------
@app.get("/")
def home():
    return {"message": "API chal rahi hai 🚀"}

# ---------------- SHIPMENTS ----------------
@app.get("/api/shipments")
def get_shipments():
    try:
        with open("shipments.json") as f:
            return JSONResponse(json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "No data"}, status_code=404)

@app.get("/api/shipments/{shipment_id}")
def get_shipment(shipment_id: str):
    with open("shipments.json") as f:
        shipments = json.load(f)
    for s in shipments:
        if s["shipment_id"] == shipment_id:
            return JSONResponse(s)
    return JSONResponse({"error": "Not found"}, status_code=404)

# ---------------- SUMMARY ----------------
@app.get("/api/summary")
def get_summary():
    with open("shipments.json") as f:
        shipments = json.load(f)
    return {
        "total": len(shipments),
        "high_risk": sum(1 for s in shipments if s["risk_level"] == "high"),
        "medium_risk": sum(1 for s in shipments if s["risk_level"] == "medium"),
        "low_risk": sum(1 for s in shipments if s["risk_level"] == "low"),
        "rerouted": sum(1 for s in shipments if s["rerouted"]),
        "total_delay_avoided": round(sum(s.get("delay_avoided_hrs", 0) for s in shipments), 1),
        "total_cost_saved": sum(s.get("cost_saved_inr", 0) for s in shipments),
        "cascade_alerts": sum(1 for s in shipments if s["risk_level"] == "high" and not s["rerouted"]),
        "last_updated": datetime.now().strftime("%H:%M:%S")
    }

# ---------------- RECOMMEND ----------------
@app.get("/api/recommend/{shipment_id}")
def recommend(shipment_id: str):
    with open("shipments.json") as f:
        shipments = json.load(f)
    for s in shipments:
        if s["shipment_id"] == shipment_id:
            return JSONResponse(get_ai_recommendation(s))
    return JSONResponse({"error": "Not found"}, status_code=404)

# ---------------- APPROVE ----------------
@app.post("/api/approve/{shipment_id}")
async def approve_reroute(shipment_id: str, request: Request):
    body = await request.json()
    operator = body.get("operator", "Dashboard Operator")
    route_choice = body.get("route_choice", "alternate_1")

    with open("shipments.json") as f:
        shipments = json.load(f)

    for s in shipments:
        if s["shipment_id"] == shipment_id:
            prev_risk = s["risk_score"]
            delay_avoided = round(random.uniform(1.5, 5.0), 1)
            cost_saved = int(delay_avoided * random.randint(8000, 15000))

            original_stops = s.get("original_route_stops", s["route_stops"].copy())

            routes = build_alternate_routes(s)
            new_stops = routes.get(route_choice, {}).get("stops", s["route_stops"])

            new_route_coords = [
                {"city": city, "lat": CITIES[city]["lat"], "lon": CITIES[city]["lon"]}
                for city in new_stops if city in CITIES
            ]

            orig_route_coords = [
                {"city": city, "lat": CITIES[city]["lat"], "lon": CITIES[city]["lon"]}
                for city in original_stops if city in CITIES
            ]

            s.update({
                "rerouted": True,
                "approved_by": operator,
                "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "risk_score": random.randint(5, 25),
                "risk_level": "low",
                "status": "rerouted",
                "delay_avoided_hrs": delay_avoided,
                "cost_saved_inr": cost_saved,
                "route_choice": route_choice,
                "new_route_stops": new_stops,
                "new_route_coords": new_route_coords,
                "original_route_stops": original_stops,
                "orig_route_coords": orig_route_coords
            })

            entry = {
                "shipment_id": shipment_id,
                "operator": operator,
                "message": f"Reroute approved. Delay avoided: {delay_avoided} hrs. Cost saved: Rs.{cost_saved}"
            }

            audit_trail.append(entry)

            with open("shipments.json", "w") as f:
                json.dump(shipments, f, indent=2)

            return JSONResponse({"success": True, "message": entry["message"]})

    return JSONResponse({"error": "Not found"}, status_code=404)

# ---------------- AUDIT ----------------
@app.get("/api/audit")
def get_audit():
    return JSONResponse(audit_trail)

# ---------------- REFRESH ----------------
@app.post("/api/refresh")
def manual_refresh():
    result = run_risk_engine()
    if result:
        _, cascades = result
        return JSONResponse({"success": True, "cascades": len(cascades)})
    return JSONResponse({"error": "Failed"}, status_code=500)

# ---------------- RESET ----------------
@app.delete("/api/reset")
def reset_data():
    generate_all_shipments(200)
    run_risk_engine()
    return JSONResponse({"success": True})
