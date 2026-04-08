# ShiftReady

An agentic daily operations briefing tool for last-mile delivery teams. Every morning before a shift, an ops manager opens ShiftReady and gets a plain-English briefing: what's happening today that affects your operation, what's going to cause problems, and exactly what to do about it.

The agent cross-references live NYC data sources and uses Claude to generate specific, actionable recommendations — not just a data dump.

---

## What it does

**Today's Briefing** — Hit "Generate Briefing" and the agent pulls all live data, reasons across it, and writes a shift brief structured around your operation:

- **Critical Alerts** — anything requiring immediate action before dispatch
- **Weather Impact** — not just the forecast, but what it means (rain → 25-40% longer delivery times, wind → reassign bike couriers to drivers, snow → driver-only operations)
- **Transit Status** — affected subway lines mapped to your delivery zones and staffing impact (L train suspended → East Village staff from Williamsburg may be 40 min late)
- **Route Disruptions** — street closures and construction cross-referenced against zones
- **Staffing Impact** — which specific employees are at risk of being late based on their commute, with one-tap contact links
- **Recommendations** — numbered action items for the next 30 minutes

**Live Conditions** — Real-time weather, subway line status, and active 311 complaints. Auto-refreshes every 5 minutes.

**Briefing History** — Every briefing saved locally. View any past day.

**Staff** — Manage your team's commute data. The lateness risk engine instantly cross-references each employee's subway lines against live transit alerts — no extra AI call needed.

---

## Live data sources

All free, no API keys required (except Anthropic).

| Source | What it provides |
|--------|-----------------|
| [National Weather Service](https://www.weather.gov/documentation/services-web-api) | Current conditions, forecast, alerts for NYC |
| [Open-Meteo](https://open-meteo.com) | Weather fallback (used automatically if NWS is down) |
| [MTA GTFS-RT Alerts](https://api-endpoint.mta.info) | Live subway service alerts for all lines |
| [NYC Open Data — Street Closures](https://data.cityofnewyork.us/resource/i5rr-er5q.json) | Active construction and closure permits |
| [NYC 311](https://data.cityofnewyork.us/resource/erm2-nwe9.json) | Recent Manhattan street/traffic complaints |

All external API responses are cached for 15 minutes. Every source fails gracefully — if MTA is down, the briefing notes it and continues with available data.

---

## Tech stack

- **Backend** — Python / FastAPI
- **Frontend** — React 18 + Vite
- **AI** — Anthropic Claude (`claude-sonnet-4-20250514`)
- **Storage** — JSON files (briefing history, employee roster)

---

## Delivery zones

The agent maps all data to five Manhattan zones:

| Zone | Coverage | Key subway lines |
|------|----------|-----------------|
| Uptown | Above 59th St | 1/2/3, 4/5/6, A/C |
| Midtown | 34th–59th St | N/Q/R/W, 4/5/6, A/C/E, B/D/F/M, 7 |
| Chelsea | 14th–34th St | 1/2/3, A/C/E, L |
| East Village | Below 14th St, East of Broadway | L, 4/5/6, J/Z |
| Downtown / FiDi | Below 14th St, West of Broadway | 1/2/3, A/C/E, J/Z, R/W |

---

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com)

### Install and run

```bash
git clone https://github.com/jtmcc17-boop/shiftready.git
cd shiftready

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

./start.sh
```

`start.sh` handles everything: creates the Python venv, installs dependencies for both backend and frontend, and starts both servers.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

Backend logs: `/tmp/shiftready-backend.log`

### Manual setup (if you prefer)

```bash
# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --port 8000 --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

---

## Environment variables

```
ANTHROPIC_API_KEY=sk-ant-...
```

That's the only required variable. All other data sources are public and keyless.

---

## Employee management

Add your team's commute info so ShiftReady can predict who might be late.

**Add individually** — use the Staff tab's "Add Employee" form. Select subway lines from a visual NYC-color-coded picker.

**Bulk upload** — upload a CSV from the Staff tab. Download the template from the upload dialog.

CSV format:
```
name,role,home_neighborhood,home_borough,subway_lines,bus_lines,commute_mode,shift_start,zone_assignment,phone,email,notes
Jane Smith,courier,Williamsburg,Brooklyn,L,B38,subway,09:00,East Village,555-0100,jane@example.com,
```

`subway_lines` and `bus_lines` are comma-separated within the cell. Set `overwrite=true` in the upload dialog to replace all existing employees.

**Risk levels:**
- **High** — employee's subway line is suspended (~40 min estimated delay)
- **Moderate** — line has delays or planned work, or bike/walk commuter in bad weather
- **Low** — no known impact

High-risk employees surface in both the Staff tab and the Staffing Impact section of Today's Briefing, with phone/email contact links.

---

## Demo mode

Toggle "Demo" in the header to switch from live data to a hardcoded scenario: heavy rain, 30 mph winds, L train suspended, Broadway construction in Chelsea. Useful for presentations or testing without waiting for real disruptions.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/briefing/generate?demo=false` | Generate a new briefing via Claude |
| `GET` | `/briefing/history` | List all saved briefings |
| `GET` | `/briefing/{id}` | Retrieve a specific briefing |
| `GET` | `/conditions?demo=false` | Raw conditions data (no Claude) |
| `GET` | `/employees` | List all employees |
| `POST` | `/employees` | Add a single employee |
| `PUT` | `/employees/{id}` | Update an employee |
| `DELETE` | `/employees/{id}` | Delete an employee |
| `POST` | `/employees/upload` | Bulk upload from CSV or JSON |
| `GET` | `/employees/risk?demo=false` | Lateness risk assessment |
| `GET` | `/employees/template` | Download CSV template |
| `GET` | `/health` | Health check |

Full interactive docs at `http://localhost:8000/docs`.

---

## Project structure

```
shiftready/
├── backend/
│   ├── main.py           # FastAPI app and all routes
│   ├── agent.py          # Claude integration and briefing generation
│   ├── data_sources.py   # Live API fetching with 15-min cache
│   ├── employees.py      # Employee CRUD and lateness risk engine
│   ├── cache.py          # In-memory TTL cache decorator
│   ├── requirements.txt
│   └── briefings/        # Saved briefing JSON files (gitignored)
├── frontend/
│   └── src/
│       ├── App.jsx                      # Root component, state, tab routing
│       ├── components/
│       │   ├── TodaysBriefing.jsx       # Main briefing view
│       │   ├── LiveConditions.jsx       # Real-time conditions tab
│       │   ├── BriefingHistory.jsx      # Past briefings tab
│       │   ├── StaffTab.jsx             # Employee management tab
│       │   └── AlertCard.jsx            # Reusable alert card
│       ├── index.css                    # Design system and all styles
│       └── main.jsx
├── .env.example
├── .gitignore
└── start.sh
```
