# ShiftReady: Agentic Daily Operations Briefing for Delivery Teams

## The Problem

Every morning, an ops manager walks into the warehouse and starts their shift blind. They check the weather on their phone, scroll Slack for overnight updates, glance at the schedule, and try to mentally piece together what kind of day it's going to be. By the time the first orders start flowing, they're already reacting instead of planning.

Meanwhile, the information they actually need is scattered across five different sources: weather forecasts, transit alerts, street closure notices, staffing schedules, and yesterday's performance. Nobody is connecting the dots between "the L train is down" and "three of your drivers take the L to work."

**ShiftReady connects those dots.** It pulls live data from public APIs, cross-references it against your operation, and generates an actionable briefing before the first order ships.

## What Makes This Different

This is not a dashboard. Dashboards show you data and let you figure out what it means. ShiftReady tells you what the data means for your operation and what to do about it.

**A weather app says:** "Rain, 60°F, 80% chance of precipitation starting at noon."

**ShiftReady says:** "Rain starting at noon will slow afternoon deliveries by 25-40%. Your 12:00-1:00 and 1:00-2:00 windows are at highest risk. Consider reducing order capacity for afternoon windows or pulling a driver from the morning shift to cover. Orders with temperature-sensitive items (dairy, chocolate) should be flagged for insulated packaging."

The difference is interpretation. The agent doesn't just fetch data — it thinks about what the data means for your specific operation and recommends specific actions.

## How It Works

ShiftReady pulls from live, free public APIs — no dummy data, no simulations. Every briefing reflects what's actually happening right now.

### Live Data Sources

| Source | What It Provides | API |
|--------|-----------------|-----|
| National Weather Service | Hourly forecast, severe weather alerts, temperature, precipitation, wind | api.weather.gov (free, no key) |
| OpenMeteo | Backup weather data, hourly breakdowns | open-meteo.com (free, no key) |
| NYC MTA | Subway and bus service disruptions, delays, planned work | MTA alerts feed (free) |
| NYC Open Data | Street closures, construction permits, road work | data.cityofnewyork.us (free) |
| NYC 311 | Recent complaints — blocked roads, traffic signals, street conditions | data.cityofnewyork.us (free) |

### Agent Intelligence

The agent cross-references data sources to surface compound impacts that no single source would reveal:

**Weather → Delivery Impact**
- Rain/snow → longer delivery times, recommend capacity reduction
- Extreme heat → flag temperature-sensitive orders for insulated packaging
- High wind → reassign bike deliveries to drivers
- Snow/ice → recommend driver-only operations

**Transit Disruptions → Staffing Impact**
- Maps each subway line to the employees who commute on it
- If the L train is suspended → "3 staff members commute via L train. Expect 20-40 min delays. Consider delaying first dispatch wave."
- Planned weekend work → flags staffing risks for weekend shifts in advance

**Staff Predictions**
- Cross-references employee commute routes with real-time transit status
- Flags specific employees likely to be late based on disruptions on their line
- Identifies potential call-out risk when severe weather or major transit outages make commuting difficult
- Recommends backup staffing actions: "Marcus and Priya both take the A train (suspended). Devon takes the F (running with delays). You may be short 2 staff for the 10am start. Alert backups now."

**Street Closures → Route Impact**
- Filters active closures and construction to your delivery zones
- "Broadway closed between 23rd-28th for construction. 12 orders in today's Chelsea queue affected. Recommend alternate routing via 6th Ave."

**Combined Intelligence**
- Rain + transit delay = "Compound impact: slower deliveries AND fewer drivers arriving on time. Recommend reducing 10am-11am window capacity by 30%."
- Heat + high volume = "95°F today with 15 orders containing dairy. Pre-stage insulated bags at packing stations."
- Street closure + driver call-out = "Downtown zone has a closure on Wall St AND you're short a driver. Reroute remaining downtown orders through East Village."

## Features

### Today's Briefing
The main view. Hit "Generate Briefing" and the agent pulls all live data, analyzes it, and produces a structured briefing:
- **Critical Alerts** — anything requiring immediate action (severe weather, major transit outage, staffing emergency)
- **Weather Impact** — what today's weather means for your operation, not just the forecast
- **Staff Status** — who might be late or unable to make it, based on their commute and current transit conditions
- **Transit Status** — affected subway lines mapped to your delivery zones
- **Route Disruptions** — street closures and construction with zone-level impact
- **Recommendations** — numbered action items the ops manager should take before the shift starts

### Staff Insights
- Shows each employee, their commute method (subway line, bus route, driving, biking)
- Real-time status of their commute route
- Risk level: green (clear commute), yellow (delays on their line), red (service suspended)
- Predicted arrival impact and recommended actions
- Historical patterns: "Marcus has been late 3 of the last 5 times the A train had delays"

### Live Conditions
- Real-time weather with hourly forecast for the next 8 hours
- Current transit status by subway line (green/yellow/red)
- Active street closures filtered to your delivery zones
- Auto-refreshes every 5 minutes

### Briefing History
- Past briefings stored by date
- Compare conditions across days to spot patterns
- "It rained 4 of the last 7 days — afternoon delivery times have averaged 35% longer"

### Demo Mode
- Toggle between "Live" (real data) and "Demo" (pre-built scenario) for presentations
- Demo scenario: rainy day, L train suspended, Broadway construction, heat advisory, 2 staff affected by transit

## Tech Stack

- **Backend**: FastAPI (Python) with Anthropic Claude API for agent intelligence
- **Frontend**: React with Vite
- **Data Sources**: National Weather Service, OpenMeteo, NYC MTA, NYC Open Data, NYC 311 — all free, no paid APIs
- **Storage**: JSON files for briefing history and staff profiles

## Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- An Anthropic API key ([get one here](https://console.anthropic.com))

### Installation

```bash
git clone https://github.com/jtmcc17-boop/shiftready.git
cd shiftready

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY

# Frontend
cd ../frontend
npm install
```

### Run

```bash
# From project root
bash start.sh
```

Or manually:

```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate && uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

## What Makes This a Real Product (Not a Demo)

Every other project in an AI PM portfolio uses dummy data. ShiftReady uses live data from public APIs. You can open it right now and verify every recommendation against reality:

- Is it actually raining? Check weather.gov.
- Is the L train actually down? Check the MTA app.
- Is Broadway actually closed at 25th? Check NYC Open Data.

The agent's value is testable in real-time. That's the difference between a prototype and a product.

## Changelog

### v1 — Initial Build (April 2026)
- Live weather integration (NWS + OpenMeteo)
- NYC MTA transit status monitoring
- NYC Open Data street closure and 311 integration
- Staff commute tracking with transit-based arrival predictions
- Agentic briefing generation with cross-referenced recommendations
- Live and Demo mode toggle
- Briefing history

## What's Next

- [ ] Integrate with DispatchIQ to automatically adjust delivery capacity based on briefing
- [ ] SMS/push alerts to staff when their commute route is disrupted
- [ ] Historical analytics: "when it rains, your afternoon OTIF drops by X%"
- [ ] Customizable delivery zones (currently hardcoded to Manhattan)
- [ ] Support for multiple cities beyond NYC
- [ ] Shift-to-shift handoff notes carried forward into next day's briefing

## Background

Built as part of a portfolio demonstrating agentic AI for frontline operations. Unlike portfolio projects that rely on synthetic data, ShiftReady connects to live public APIs to prove the agent's recommendations are accurate and useful in the real world. The staff insights feature reflects a real operational pain point: when the subway breaks, your shift is short-staffed, and nobody knows until people don't show up.

Part of a connected worker portfolio that includes [CareLog](https://github.com/jtmcc17-boop/carelog) (healthcare frontline) and [DispatchIQ](https://github.com/jtmcc17-boop/dispatchiq) (delivery operations).

## License

MIT
