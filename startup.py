import os
import json

# Generate shipments if not exists
if not os.path.exists("shipments.json"):
    from mock_data import generate_all_shipments
    generate_all_shipments(200)
    print("Generated fresh shipments for deployment")

# Start the risk engine once
from risk_engine import run_risk_engine
run_risk_engine()
print("Initial risk calculation done")
