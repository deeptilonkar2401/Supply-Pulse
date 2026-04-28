import json
import random
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# City coordinates (same as mock_data)
CITIES = {
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777},
    "Delhi":     {"lat": 28.6139, "lon": 77.2090},
    "Kolkata":   {"lat": 22.5726, "lon": 88.3639},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "Pune":      {"lat": 18.5204, "lon": 73.8567},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "Jaipur":    {"lat": 26.9124, "lon": 75.7873},
    "Nagpur":    {"lat": 21.1458, "lon": 79.0882},
    "Lucknow":   {"lat": 26.8467, "lon": 80.9462},
    "Bhopal":    {"lat": 23.2599, "lon": 77.4126},
    "Surat":     {"lat": 21.1702, "lon": 72.8311},
    "Indore":    {"lat": 22.7196, "lon": 75.8577},
    "Raipur":    {"lat": 21.2514, "lon": 81.6296},
}

# Cache weather data to avoid too many API calls
weather_cache = {}


def get_real_weather_score(location):
    """
    Fetch REAL weather using Open-Meteo API.
    Completely FREE — no API key needed, no restrictions, works on localhost.
    """
    # Use cache — avoid too many calls (cache 10 min)
    if location in weather_cache:
        cached_time, cached_score, cached_desc = weather_cache[location]
        if (datetime.now() - cached_time).seconds < 600:
            return cached_score, cached_desc

    try:
        city = CITIES.get(location)
        if not city:
            return get_simulated_weather_score(location)

        lat, lon = city["lat"], city["lon"]

        # Open-Meteo — free, no key, no allowlist issues
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"precipitation,wind_speed_10m,weather_code,visibility"
            f"&timezone=Asia%2FKolkata"
        )
        response = requests.get(url, timeout=8)

        if response.status_code != 200:
            return get_simulated_weather_score(location)

        data    = response.json()
        current = data["current"]

        temp       = round(current.get("temperature_2m", 30), 1)
        humidity   = current.get("relative_humidity_2m", 50)
        wind_kmph  = round(current.get("wind_speed_10m", 0), 1)
        precip     = current.get("precipitation", 0)
        vis_m      = current.get("visibility", 10000)
        wmo_code   = current.get("weather_code", 0)

        # WMO weather code to description
        wmo_desc = {
            0:"Clear Sky", 1:"Mainly Clear", 2:"Partly Cloudy", 3:"Overcast",
            45:"Foggy", 48:"Icy Fog",
            51:"Light Drizzle", 53:"Moderate Drizzle", 55:"Dense Drizzle",
            61:"Slight Rain", 63:"Moderate Rain", 65:"Heavy Rain",
            71:"Slight Snow", 73:"Moderate Snow", 75:"Heavy Snow",
            77:"Snow Grains", 80:"Slight Showers", 81:"Moderate Showers",
            82:"Violent Showers", 85:"Snow Showers", 86:"Heavy Snow Showers",
            95:"Thunderstorm", 96:"Thunderstorm+Hail", 99:"Thunderstorm+Heavy Hail"
        }
        desc_text = wmo_desc.get(wmo_code, f"Code {wmo_code}")

        # Risk score from WMO code
        if wmo_code in [95, 96, 99]:    score = 90   # Thunderstorm
        elif wmo_code in [65, 82]:       score = 70   # Heavy rain
        elif wmo_code in [63, 81, 75]:   score = 60   # Moderate rain
        elif wmo_code in [45, 48]:       score = 65   # Fog
        elif wmo_code in [61, 80, 73]:   score = 45   # Slight rain
        elif wmo_code in [51, 53, 55]:   score = 30   # Drizzle
        elif wmo_code in [3]:            score = 20   # Overcast
        elif wmo_code in [2]:            score = 15   # Partly cloudy
        elif wmo_code in [0, 1]:         score = 10   # Clear
        else:                            score = 25

        # Wind bonus
        if wind_kmph > 50:   score += 20
        elif wind_kmph > 30: score += 10
        elif wind_kmph > 20: score += 5

        # Humidity bonus
        if humidity > 90: score += 10
        elif humidity > 80: score += 5

        # Precipitation bonus
        if precip > 10: score += 15
        elif precip > 5: score += 8
        elif precip > 1: score += 4

        final_score = min(100, score)
        desc = f"{desc_text} | {temp}C | Wind:{wind_kmph}kmh | Humidity:{humidity}%"

        weather_cache[location] = (datetime.now(), final_score, desc)
        print(f"  REAL weather {location}: {desc} -> Risk:{final_score}")
        return final_score, desc

    except requests.exceptions.Timeout:
        print(f"  Weather timeout {location} -> simulation")
        return get_simulated_weather_score(location)
    except Exception as e:
        print(f"  Weather error {location}: {e} -> simulation")
        return get_simulated_weather_score(location)


def calculate_weather_risk_from_api(weather_id, wind_speed, humidity, visibility):
    """
    Convert real weather data into a risk score 0-100.

    OpenWeather ID ranges:
    2xx = Thunderstorm  -> very high risk
    3xx = Drizzle       -> low risk
    5xx = Rain          -> medium-high risk
    6xx = Snow          -> high risk
    7xx = Atmosphere (fog, haze, dust) -> medium risk
    800 = Clear sky     -> low risk
    80x = Clouds        -> low-medium risk
    """
    base_score = 0

    # Weather condition score
    # wttr.in codes + OpenWeather codes both handled
    if weather_id in [389, 386, 200, 201, 202]:   # Thunderstorm with rain/hail
        base_score = 90
    elif weather_id in [392, 395, 232, 231, 230]:  # Thunder with snow/ice
        base_score = 85
    elif weather_id in [377, 374, 371, 368]:        # Ice/sleet
        base_score = 80
    elif weather_id in [365, 362, 338, 335]:        # Snow + rain mix
        base_score = 70
    elif weather_id in [359, 356, 308, 305]:        # Heavy rain
        base_score = 65
    elif weather_id in [353, 350, 302, 299]:        # Moderate rain
        base_score = 55
    elif weather_id in [266, 263, 185, 182]:        # Light drizzle/rain
        base_score = 35
    elif weather_id in [284, 281]:                  # Freezing drizzle
        base_score = 60
    elif weather_id in [248, 260]:                  # Fog/freezing fog
        base_score = 70
    elif weather_id in [143]:                       # Mist
        base_score = 40
    elif weather_id in [119, 122]:                  # Overcast/cloudy
        base_score = 20
    elif weather_id in [116]:                       # Partly cloudy
        base_score = 15
    elif weather_id in [113]:                       # Sunny/clear
        base_score = 10
    # OpenWeather codes fallback
    elif 200 <= weather_id <= 232:
        base_score = 85
    elif 300 <= weather_id <= 321:
        base_score = 25
    elif 500 <= weather_id <= 531:
        base_score = 60
    elif 600 <= weather_id <= 622:
        base_score = 75
    elif 700 <= weather_id <= 781:
        base_score = 55
    elif weather_id == 800:
        base_score = 10
    elif 801 <= weather_id <= 804:
        base_score = 20
    else:
        base_score = 30

    # Add wind speed penalty (>10 m/s is dangerous for trucks)
    if wind_speed > 20:
        base_score += 20
    elif wind_speed > 15:
        base_score += 12
    elif wind_speed > 10:
        base_score += 6

    # Add humidity penalty (>85% means heavy moisture, fog likely)
    if humidity > 90:
        base_score += 10
    elif humidity > 80:
        base_score += 5

    # Low visibility penalty
    if visibility < 1000:
        base_score += 20
    elif visibility < 3000:
        base_score += 10
    elif visibility < 5000:
        base_score += 5

    return min(100, base_score)


def get_simulated_weather_score(location):
    """
    Realistic weather simulation based on actual Indian seasonal patterns.
    Uses current month to simulate realistic conditions.
    """
    from datetime import datetime
    month = datetime.now().month

    # April-June = hot/dry, July-Sept = monsoon, Oct-Nov = post monsoon, Dec-Mar = winter
    # Each city has realistic risk ranges per season
    seasonal_risk = {
        # format: (monsoon_range, summer_range, winter_range)
        "Mumbai":    [(60,95), (20,55), (10,35)],  # heavy monsoon city
        "Delhi":     [(30,70), (25,65), (10,40)],  # dusty summers
        "Kolkata":   [(65,95), (30,60), (10,35)],  # very heavy monsoon
        "Chennai":   [(50,90), (20,50), (40,80)],  # northeast monsoon Oct-Dec
        "Bangalore": [(30,65), (10,40), (10,30)],  # mild city
        "Hyderabad": [(40,75), (20,55), (10,35)],
        "Pune":      [(45,80), (15,45), (10,30)],
        "Ahmedabad": [(25,60), (20,55), (5,25)],
        "Jaipur":    [(20,55), (25,60), (5,25)],   # dry city
        "Nagpur":    [(50,85), (30,70), (10,35)],  # extreme heat + monsoon
        "Lucknow":   [(40,75), (20,55), (15,45)],  # fog in winter
        "Bhopal":    [(45,80), (20,55), (10,35)],
        "Surat":     [(55,90), (20,50), (10,30)],  # coastal heavy rain
        "Indore":    [(40,75), (20,50), (10,35)],
        "Raipur":    [(55,90), (25,60), (10,35)],  # high monsoon
    }

    # Determine season
    if 6 <= month <= 9:    # Monsoon
        idx = 0
        season = "Monsoon"
    elif 3 <= month <= 5:  # Summer
        idx = 1
        season = "Summer"
    else:                  # Winter
        idx = 2
        season = "Winter"

    ranges = seasonal_risk.get(location, [(40,75),(20,55),(10,35)])
    lo, hi = ranges[idx]
    score = random.randint(lo, hi)

    # Weather descriptions based on score
    if score >= 75:
        desc = f"{season}: Heavy Rain / Thunderstorm"
    elif score >= 55:
        desc = f"{season}: Moderate Rain / Cloudy"
    elif score >= 35:
        desc = f"{season}: Partly Cloudy / Light Wind"
    else:
        desc = f"{season}: Clear Sky"

    return score, desc


def calculate_traffic_score(location):
    """Simulated traffic — replace with Google Maps API if needed"""
    traffic = {
        "Mumbai":    random.randint(55, 95),
        "Delhi":     random.randint(55, 95),
        "Kolkata":   random.randint(40, 88),
        "Chennai":   random.randint(35, 85),
        "Bangalore": random.randint(55, 95),
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
    return traffic.get(location, random.randint(20, 70))


def calculate_historical_delay_score(route_stops):
    """Simulated historical delay rate"""
    base  = len(route_stops) * 8
    noise = random.randint(-15, 25)
    return min(100, max(0, base + noise))


def get_risk_level(score, sensitivity):
    if sensitivity == "critical":
        if score >= 55: return "high"
        if score >= 35: return "medium"
        return "low"
    elif sensitivity == "high":
        if score >= 65: return "high"
        if score >= 45: return "medium"
        return "low"
    elif sensitivity == "medium":
        if score >= 70: return "high"
        if score >= 50: return "medium"
        return "low"
    else:
        if score >= 80: return "high"
        if score >= 60: return "medium"
        return "low"


def calculate_risk_score(shipment):
    """4-factor weighted risk score with REAL weather"""
    current_loc = shipment["current_location"]
    route_stops = shipment["route_stops"]
    multiplier  = shipment["risk_multiplier"]

    # Real weather score
    weather_result = get_real_weather_score(current_loc)
    if isinstance(weather_result, tuple):
        weather_score, weather_desc = weather_result
    else:
        weather_score, weather_desc = weather_result, "Unknown"

    traffic_score    = calculate_traffic_score(current_loc)
    historical_score = calculate_historical_delay_score(route_stops)
    sensitivity_map  = {"critical": 80, "high": 60, "medium": 40, "low": 20}
    cargo_score      = sensitivity_map.get(shipment["sensitivity"], 40)

    raw_score = (
        weather_score    * 0.35 +
        traffic_score    * 0.30 +
        historical_score * 0.20 +
        cargo_score      * 0.15
    )
    final_score = min(100, round(raw_score * multiplier))

    return {
        "final_score":       final_score,
        "weather_score":     weather_score,
        "weather_desc":      weather_desc,
        "traffic_score":     traffic_score,
        "historical_score":  historical_score,
        "cargo_score":       cargo_score,
    }


def find_cascade_shipments(affected_location, all_shipments, current_id):
    """Cascade propagation — find all shipments sharing same corridor"""
    return [
        s["shipment_id"] for s in all_shipments
        if s["shipment_id"] != current_id
        and affected_location in s["route_stops"]
    ]


def run_risk_engine():
    try:
        with open("shipments.json", "r") as f:
            shipments = json.load(f)
    except FileNotFoundError:
        print("shipments.json not found. Run mock_data.py first.")
        return []

    cascade_warnings = {}
    api_mode = "REAL API" if OPENWEATHER_API_KEY else "SIMULATED"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running risk engine ({api_mode} weather)...")

    for shipment in shipments:
        if shipment["rerouted"]:
            continue

        scores = calculate_risk_score(shipment)
        shipment["risk_score"]      = scores["final_score"]
        shipment["weather_score"]   = scores["weather_score"]
        shipment["weather_desc"]    = scores.get("weather_desc", "")
        shipment["traffic_score"]   = scores["traffic_score"]
        shipment["historical_score"]= scores["historical_score"]
        shipment["cargo_score"]     = scores["cargo_score"]
        shipment["risk_level"]      = get_risk_level(
            scores["final_score"], shipment["sensitivity"]
        )

        if shipment["risk_level"] == "high":
            cascade_ids = find_cascade_shipments(
                shipment["current_location"], shipments, shipment["shipment_id"]
            )
            if cascade_ids:
                cascade_warnings[shipment["shipment_id"]] = {
                    "location":    shipment["current_location"],
                    "cascade_ids": cascade_ids,
                    "count":       len(cascade_ids)
                }

    with open("shipments.json", "w") as f:
        json.dump(shipments, f, indent=2)

    high   = sum(1 for s in shipments if s["risk_level"] == "high")
    medium = sum(1 for s in shipments if s["risk_level"] == "medium")
    low    = sum(1 for s in shipments if s["risk_level"] == "low")
    print(f"  Done -> HIGH: {high} | MEDIUM: {medium} | LOW: {low} | Cascades: {len(cascade_warnings)}")

    return shipments, cascade_warnings


if __name__ == "__main__":
    print("Testing risk engine...")
    result = run_risk_engine()
    if result:
        shipments, cascades = result
        print(f"\nCascade warnings: {len(cascades)}")
        for sid, info in cascades.items():
            print(f"  {sid} at {info['location']} -> affects {info['count']} shipments")
