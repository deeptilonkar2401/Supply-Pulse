from flask import Flask, jsonify, request
from datetime import datetime
from ai_recommender import get_ai_recommendation

app = Flask(__name__)

shipments = {}  # assume your data already here


@app.route("/api/recommend/<sid>")
def recommend(sid):
    shipment = shipments[sid]
    return jsonify(get_ai_recommendation(shipment))


@app.route("/api/approve/<sid>", methods=["POST"])
def approve(sid):
    shipment = shipments[sid]

    # build routes
    from ai_recommender import build_alternate_routes
    routes = build_alternate_routes(shipment)

    original = routes["original"]
    alt1 = routes["alt1"]

    # FIXED METRICS (NO RANDOM NOW)
    delay = original["hours"] - alt1["hours"]
    cost_saved = max(0, delay * 1200)

    shipment["rerouted"] = True
    shipment["orig_route_coords"] = original["coords"]
    shipment["new_route_coords"] = alt1["coords"]

    shipment["original_route_stops"] = original["stops"]
    shipment["new_route_stops"] = alt1["stops"]

    shipment["delay_avoided_hrs"] = delay
    shipment["cost_saved_inr"] = cost_saved

    shipment["approved_by"] = "Dashboard Operator"
    shipment["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "success": True,
        "shipment": shipment
    })


@app.route("/api/shipments")
def all_shipments():
    return jsonify(list(shipments.values()))


@app.route("/api/shipments/<sid>")
def get_one(sid):
    return jsonify(shipments[sid])


if __name__ == "__main__":
    app.run(debug=True)
