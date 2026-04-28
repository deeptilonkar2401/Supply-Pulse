from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from apscheduler.schedulers.background import BackgroundScheduler

import json, os, random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from mock_data import generate_all_shipments, CITIES
from risk_engine import run_risk_engine
from ai_recommender import get_ai_recommendation, build_alternate_routes

app = FastAPI(title="SupplyPulse")

# ----------- DATA INIT -----------
if not os.path.exists("shipments.json"):
    generate_all_shipments(200)

# 🔥 IMPORTANT: run risk engine at startup
run_risk_engine()

# ----------- SCHEDULER (REAL-TIME FEEL) -----------
scheduler = BackgroundScheduler()
scheduler.add_job(run_risk_engine, "interval", seconds=60)
scheduler.start()

# ----------- FRONTEND -----------
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

audit_trail = []

# ----------- HOME (UI) -----------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ----------- SHIPMENTS -----------
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

# ----------- SUMMARY -----------
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
        "last_updated": datetime.now().strftime("%H:%M:%S")
    }

# ----------- AI RECOMMEND -----------
@app.get("/api/recommend/{shipment_id}")
def recommend(shipment_id: str):
    with open("shipments.json") as f:
        shipments = json.load(f)
    for s in shipments:
        if s["shipment_id"] == shipment_id:
            return JSONResponse(get_ai_recommendation(s))
    return JSONResponse({"error": "Not found"}, status_code=404)

# ----------- APPROVE -----------
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

            routes = build_alternate_routes(s)
            new_stops = routes.get(route_choice, {}).get("stops", s["route_stops"])

            s["rerouted"] = True
            s["risk_level"] = "low"
            s["risk_score"] = random.randint(5, 25)
            s["approved_by"] = operator
            s["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            s["new_route_stops"] = new_stops

            with open("shipments.json", "w") as f:
                json.dump(shipments, f, indent=2)

            return JSONResponse({
                "success": True,
                "message": f"Rerouted. Risk {prev_risk} → {s['risk_score']}",
                "new_route": new_stops
            })

    return JSONResponse({"error": "Not found"}, status_code=404)

# ----------- RESET -----------
@app.delete("/api/reset")
def reset_data():
    generate_all_shipments(200)
    run_risk_engine()
    return JSONResponse({"success": True})
