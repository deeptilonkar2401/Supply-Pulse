<<<<<<< HEAD
# SupplyPulse 🚛
### AI-Powered Supply Chain Disruption Detection System

> **"Jo problem aaj 5 ghante baad pata chalti hai, woh humara system 5 ghante PEHLE bata deta hai."**

---

## Problem Statement
Modern supply chains manage millions of shipments across complex transportation networks. Critical transit disruptions — weather events, traffic bottlenecks — are identified **only after delivery timelines are already compromised**.

## Our Solution
SupplyPulse is a real-time dashboard that:
- **Predicts** disruptions before they happen
- **Cascades** alerts to all affected downstream shipments
- **Recommends** AI-powered rerouting options instantly
- **Tracks** cost savings and delay avoided in real time

---

## Unique Features
| Feature | Description |
|---|---|
| Cargo-aware risk scoring | Pharmaceuticals flagged at score 55, Steel at 80 |
| Cascade propagation | 1 blocked route → alerts all downstream shipments |
| 6-24hr predictive alerts | Weather forecast + history = proactive warnings |
| Claude AI rerouting | Plain English recommendations with cost trade-offs |
| Audit trail | Every reroute logged with hours saved + cost saved |

---

## Tech Stack
- **Backend:** Python, FastAPI, APScheduler
- **AI:** Anthropic Claude API
- **Weather:** OpenWeather API (real-time)
- **Frontend:** HTML, CSS, JavaScript, Leaflet.js
- **Data:** Pandas, NumPy

---

## Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create `.env` file
```
ANTHROPIC_API_KEY=your_claude_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

### 3. Generate shipment data
```bash
python mock_data.py
```

### 4. Run the server
```bash
uvicorn main:app --reload
```

### 5. Open browser
```
http://localhost:8000
```

---

## How to Demo
1. Click **High** filter → see all high risk shipments
2. Click any red shipment → view risk breakdown
3. Click **Get AI Recommendation** → Claude suggests reroute
4. Click **Approve Reroute** → route updates on map
5. Click **Rerouted** filter → see original vs new route

---

## Impact Metrics
- Real-time monitoring of 200+ shipments
- Cascade detection across shared corridors
- Average 2-5 hours delay avoided per reroute
- Cost savings tracked per approval

---

## Future Potential
- Real GPS tracking via IoT sensors
- WhatsApp/SMS alerts to drivers
- ML model for 90%+ prediction accuracy
- Insurance company API integration
- Driver mobile app

---

*Built for Smart Supply Chain Hackathon 2025*
=======
# Supply-Pulse
AI-powered supply chain disruption detection system.  Built with Python, FastAPI, Claude AI, OpenWeather API. Real-time risk scoring, cascade propagation, and  automated rerouting recommendations.
>>>>>>> 18d6cd2acbfc6a5353695e0162b4e803bfe919b3
