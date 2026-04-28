from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
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

audit_trail = []
scheduler   = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists("shipments.json"):
        generate_all_shipments(200)
        print("Generated 200 shipments.")
    scheduler.add_job(scheduled_risk_update,"interval",seconds=60)
    scheduler.start()
    print("Scheduler started.")
    yield
    scheduler.shutdown()

app = FastAPI(title="SupplyPulse", lifespan=lifespan)
os.makedirs("static",exist_ok=True)
os.makedirs("templates",exist_ok=True)
app.mount("/static",StaticFiles(directory="static"),name="static")
templates = Jinja2Templates(directory="templates")

def scheduled_risk_update():
    result=run_risk_engine()
    if result:
        _,cascades=result
        print(f"[Auto] Risk update. Cascades: {len(cascades)}")

@app.get("/",response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html",{"request":request})

@app.get("/api/shipments")
def get_shipments():
    try:
        with open("shipments.json") as f: return JSONResponse(json.load(f))
    except FileNotFoundError: return JSONResponse({"error":"No data"},status_code=404)

@app.get("/api/shipments/{shipment_id}")
def get_shipment(shipment_id: str):
    with open("shipments.json") as f: shipments=json.load(f)
    for s in shipments:
        if s["shipment_id"]==shipment_id: return JSONResponse(s)
    return JSONResponse({"error":"Not found"},status_code=404)

@app.get("/api/summary")
def get_summary():
    with open("shipments.json") as f: shipments=json.load(f)
    return {
        "total":len(shipments),
        "high_risk":sum(1 for s in shipments if s["risk_level"]=="high"),
        "medium_risk":sum(1 for s in shipments if s["risk_level"]=="medium"),
        "low_risk":sum(1 for s in shipments if s["risk_level"]=="low"),
        "rerouted":sum(1 for s in shipments if s["rerouted"]),
        "total_delay_avoided":round(sum(s.get("delay_avoided_hrs",0) for s in shipments),1),
        "total_cost_saved":sum(s.get("cost_saved_inr",0) for s in shipments),
        "cascade_alerts":sum(1 for s in shipments if s["risk_level"]=="high" and not s["rerouted"]),
        "last_updated":datetime.now().strftime("%H:%M:%S")
    }

@app.get("/api/recommend/{shipment_id}")
def recommend(shipment_id: str):
    with open("shipments.json") as f: shipments=json.load(f)
    for s in shipments:
        if s["shipment_id"]==shipment_id: return JSONResponse(get_ai_recommendation(s))
    return JSONResponse({"error":"Not found"},status_code=404)

@app.post("/api/approve/{shipment_id}")
async def approve_reroute(shipment_id: str, request: Request):
    body=await request.json()
    operator=body.get("operator","Dashboard Operator")
    route_choice=body.get("route_choice","alternate_1")

    with open("shipments.json") as f: shipments=json.load(f)

    for s in shipments:
        if s["shipment_id"]==shipment_id:
            prev_risk=s["risk_score"]
            delay_avoided=round(random.uniform(1.5,5.0),1)
            cost_saved=int(delay_avoided*random.randint(8000,15000))

            # Save original route before changing
            original_stops = s.get("original_route_stops", s["route_stops"].copy())

            # Build new route (bypass current blocked location)
            routes = build_alternate_routes(s)
            new_stops = routes.get(route_choice,{}).get("stops", s["route_stops"])

            # Get coordinates for new route stops
            new_route_coords = []
            for city in new_stops:
                if city in CITIES:
                    new_route_coords.append({
                        "city": city,
                        "lat":  CITIES[city]["lat"],
                        "lon":  CITIES[city]["lon"]
                    })

            # Get coordinates for original route stops
            orig_route_coords = []
            for city in original_stops:
                if city in CITIES:
                    orig_route_coords.append({
                        "city": city,
                        "lat":  CITIES[city]["lat"],
                        "lon":  CITIES[city]["lon"]
                    })

            # Update shipment
            s["rerouted"]          = True
            s["approved_by"]       = operator
            s["approved_at"]       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            s["risk_score"]        = random.randint(5,25)
            s["risk_level"]        = "low"
            s["status"]            = "rerouted"
            s["delay_avoided_hrs"] = delay_avoided
            s["cost_saved_inr"]    = cost_saved
            s["route_choice"]      = route_choice
            s["new_route_stops"]   = new_stops
            s["new_route_coords"]  = new_route_coords
            s["original_route_stops"] = original_stops
            s["orig_route_coords"] = orig_route_coords

            entry={
                "shipment_id":shipment_id,"cargo_type":s["cargo_type"],
                "origin":s["origin"],"destination":s["destination"],
                "operator":operator,"route_choice":route_choice,
                "original_route":original_stops,"new_route":new_stops,
                "prev_risk_score":prev_risk,"new_risk_score":s["risk_score"],
                "delay_avoided":delay_avoided,"cost_saved_inr":cost_saved,
                "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message":f"Reroute approved. Delay avoided: {delay_avoided}hrs. Cost saved: Rs.{cost_saved:,}. Risk {prev_risk} -> {s['risk_score']}."
            }
            audit_trail.append(entry)

            with open("shipments.json","w") as f: json.dump(shipments,f,indent=2)

            return JSONResponse({
                "success":True,"message":entry["message"],
                "delay_avoided":delay_avoided,"cost_saved":cost_saved,
                "new_risk_score":s["risk_score"],
                "new_route":new_stops,"original_route":original_stops
            })

    return JSONResponse({"error":"Not found"},status_code=404)

@app.get("/api/audit")
def get_audit(): return JSONResponse(audit_trail)

@app.post("/api/refresh")
def manual_refresh():
    result=run_risk_engine()
    if result:
        _,cascades=result
        return JSONResponse({"success":True,"message":"Done","cascades":len(cascades)})
    return JSONResponse({"error":"Failed"},status_code=500)

@app.delete("/api/reset")
def reset_data():
    generate_all_shipments(200)
    run_risk_engine()
    return JSONResponse({"success":True,"message":"Reset with 200 fresh shipments"})
