import random, json
from datetime import datetime, timedelta

CITIES = {
    "Mumbai":    {"lat":19.0760,"lon":72.8777},
    "Delhi":     {"lat":28.6139,"lon":77.2090},
    "Kolkata":   {"lat":22.5726,"lon":88.3639},
    "Chennai":   {"lat":13.0827,"lon":80.2707},
    "Bangalore": {"lat":12.9716,"lon":77.5946},
    "Hyderabad": {"lat":17.3850,"lon":78.4867},
    "Pune":      {"lat":18.5204,"lon":73.8567},
    "Ahmedabad": {"lat":23.0225,"lon":72.5714},
    "Jaipur":    {"lat":26.9124,"lon":75.7873},
    "Nagpur":    {"lat":21.1458,"lon":79.0882},
    "Lucknow":   {"lat":26.8467,"lon":80.9462},
    "Bhopal":    {"lat":23.2599,"lon":77.4126},
    "Surat":     {"lat":21.1702,"lon":72.8311},
    "Indore":    {"lat":22.7196,"lon":75.8577},
    "Raipur":    {"lat":21.2514,"lon":81.6296},
}
CARGO_TYPES=[
    {"type":"Pharmaceuticals","sensitivity":"critical","risk_multiplier":1.8,"value_inr":500000},
    {"type":"Frozen Food","sensitivity":"critical","risk_multiplier":1.7,"value_inr":300000},
    {"type":"Fresh Vegetables","sensitivity":"high","risk_multiplier":1.5,"value_inr":150000},
    {"type":"Electronics","sensitivity":"high","risk_multiplier":1.4,"value_inr":800000},
    {"type":"Textiles","sensitivity":"medium","risk_multiplier":1.1,"value_inr":200000},
    {"type":"Automobile Parts","sensitivity":"medium","risk_multiplier":1.0,"value_inr":350000},
    {"type":"Steel","sensitivity":"low","risk_multiplier":0.7,"value_inr":100000},
    {"type":"Cement","sensitivity":"low","risk_multiplier":0.6,"value_inr":80000},
    {"type":"Coal","sensitivity":"low","risk_multiplier":0.5,"value_inr":60000},
]
ROUTES=[
    ["Mumbai","Pune","Nagpur","Raipur","Kolkata"],
    ["Mumbai","Surat","Ahmedabad","Jaipur","Delhi"],
    ["Delhi","Lucknow","Bhopal","Nagpur","Hyderabad"],
    ["Chennai","Bangalore","Hyderabad","Nagpur","Mumbai"],
    ["Kolkata","Raipur","Nagpur","Pune","Mumbai"],
    ["Delhi","Jaipur","Ahmedabad","Surat","Mumbai"],
    ["Bangalore","Chennai","Hyderabad","Nagpur","Bhopal"],
    ["Ahmedabad","Indore","Bhopal","Nagpur","Raipur"],
    ["Mumbai","Pune","Hyderabad","Chennai","Bangalore"],
    ["Delhi","Lucknow","Kolkata","Bhopal","Nagpur"],
    ["Jaipur","Delhi","Lucknow","Kolkata","Raipur"],
    ["Surat","Mumbai","Pune","Hyderabad","Chennai"],
]
VEHICLES=["Truck","Mini Truck","Container","Tanker","Refrigerated Van"]
OPERATORS=["Rajesh Kumar","Priya Sharma","Amit Singh","Sunita Patel","Vikram Rao","Deepa Nair","Suresh Gupta","Meena Joshi","Arjun Mehta"]
STATUSES=["in_transit","in_transit","in_transit","delayed","at_checkpoint"]

def get_risk_level(score,sensitivity):
    if sensitivity=="critical":
        if score>=55:return "high"
        if score>=35:return "medium"
        return "low"
    elif sensitivity=="high":
        if score>=65:return "high"
        if score>=45:return "medium"
        return "low"
    elif sensitivity=="medium":
        if score>=70:return "high"
        if score>=50:return "medium"
        return "low"
    else:
        if score>=80:return "high"
        if score>=60:return "medium"
        return "low"

def generate_shipment(shipment_id):
    route_stops=random.choice(ROUTES)
    origin=route_stops[0]; destination=route_stops[-1]
    cargo_info=random.choice(CARGO_TYPES)
    hours_ago=random.randint(1,20)
    departure_time=datetime.now()-timedelta(hours=hours_ago)
    eta=departure_time+timedelta(hours=random.randint(24,72))
    current_stop_idx=min(hours_ago//6,len(route_stops)-2)
    current_location=route_stops[current_stop_idx]
    initial_risk=random.randint(10,85)
    return {
        "shipment_id":f"SP{shipment_id:04d}","origin":origin,"destination":destination,
        "route_stops":route_stops,"current_location":current_location,
        "cargo_type":cargo_info["type"],"sensitivity":cargo_info["sensitivity"],
        "risk_multiplier":cargo_info["risk_multiplier"],"cargo_value_inr":cargo_info["value_inr"],
        "vehicle_type":random.choice(VEHICLES),"operator":random.choice(OPERATORS),
        "weight_tons":round(random.uniform(1.0,25.0),1),
        "departure_time":departure_time.strftime("%Y-%m-%d %H:%M"),
        "eta":eta.strftime("%Y-%m-%d %H:%M"),
        "status":random.choice(STATUSES),"risk_score":initial_risk,
        "risk_level":get_risk_level(initial_risk,cargo_info["sensitivity"]),
        "weather_score":0,"traffic_score":0,"historical_score":0,"cargo_score":0,
        "weather_desc":"","rerouted":False,"approved_by":None,"delay_avoided_hrs":0.0,"cost_saved_inr":0,
        "original_route_stops":route_stops.copy(),"new_route_stops":[],
        "origin_lat":CITIES[origin]["lat"],"origin_lon":CITIES[origin]["lon"],
        "dest_lat":CITIES[destination]["lat"],"dest_lon":CITIES[destination]["lon"],
        "current_lat":CITIES[current_location]["lat"],"current_lon":CITIES[current_location]["lon"],
    }

def generate_all_shipments(count=200):
    shipments=[generate_shipment(i) for i in range(1,count+1)]
    with open("shipments.json","w") as f: json.dump(shipments,f,indent=2)
    high=sum(1 for s in shipments if s["risk_level"]=="high")
    medium=sum(1 for s in shipments if s["risk_level"]=="medium")
    low=sum(1 for s in shipments if s["risk_level"]=="low")
    print(f"Generated {count} shipments -> shipments.json")
    print(f"HIGH: {high} | MEDIUM: {medium} | LOW: {low}")
    return shipments

if __name__=="__main__":
    generate_all_shipments(200)
