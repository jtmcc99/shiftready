"""
data_sources.py — fetch live public data for ShiftReady ops briefings.

All network calls are cached for 15 minutes and fail gracefully.
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

import httpx

from cache import cached

# ── Shared HTTP headers ───────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": "ShiftReady/1.0 ops@shiftready.app",
    "Accept": "application/json",
}

# ── WMO weather-code mapping ──────────────────────────────────────────────────
WMO_CONDITIONS = {  # type: Dict[int, tuple]
    0:  ("Clear Sky", "☀️"),
    1:  ("Mainly Clear", "⛅"),
    2:  ("Partly Cloudy", "⛅"),
    3:  ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Icy Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Moderate Drizzle", "🌦️"),
    55: ("Heavy Drizzle", "🌦️"),
    56: ("Freezing Drizzle", "🌦️"),
    57: ("Heavy Freezing Drizzle", "🌦️"),
    61: ("Light Rain", "🌧️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    66: ("Freezing Rain", "🌧️"),
    67: ("Heavy Freezing Rain", "🌧️"),
    71: ("Light Snow", "❄️"),
    73: ("Moderate Snow", "❄️"),
    75: ("Heavy Snow", "❄️"),
    77: ("Snow Grains", "❄️"),
    80: ("Light Rain Showers", "🌧️"),
    81: ("Moderate Rain Showers", "🌧️"),
    82: ("Heavy Rain Showers", "🌧️"),
    85: ("Snow Showers", "❄️"),
    86: ("Heavy Snow Showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with Hail", "⛈️"),
    99: ("Thunderstorm with Heavy Hail", "⛈️"),
}


def _wmo_label(code: int) -> tuple[str, str]:
    """Return (conditions_string, emoji) for a WMO code."""
    return WMO_CONDITIONS.get(code, ("Unknown", "🌡️"))


def _f_to_c(f: float) -> float:
    return round((f - 32) * 5 / 9, 1)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Weather ───────────────────────────────────────────────────────────────────

@cached(ttl=900)
async def get_weather() -> dict:
    """Try NWS first, fall back to Open-Meteo."""
    try:
        return await _weather_nws()
    except Exception as exc:
        print(f"[weather] NWS failed ({exc}), falling back to Open-Meteo", file=sys.stderr)
    try:
        return await _weather_openmeteo()
    except Exception as exc:
        print(f"[weather] Open-Meteo also failed: {exc}", file=sys.stderr)
        return _empty_weather("unavailable")


async def _weather_nws() -> dict:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        # Step 1: points lookup
        r = await client.get(
            "https://api.weather.gov/points/40.7128,-74.0060",
            headers=_HEADERS,
        )
        r.raise_for_status()
        props = r.json()["properties"]
        forecast_url = props["forecast"]
        hourly_url = props["forecastHourly"]

        # Step 2: fetch both forecast endpoints
        daily_r, hourly_r = await asyncio.gather(
            client.get(forecast_url, headers=_HEADERS),
            client.get(hourly_url, headers=_HEADERS),
        )
        daily_r.raise_for_status()
        hourly_r.raise_for_status()

        daily_periods = daily_r.json()["properties"]["periods"]
        hourly_periods = hourly_r.json()["properties"]["periods"]

    # Today's summary periods
    today_day = next((p for p in daily_periods if p["isDaytime"]), daily_periods[0])
    today_night = next((p for p in daily_periods if not p["isDaytime"]), None)

    high_f = today_day["temperature"]
    low_f = today_night["temperature"] if today_night else None

    # Up to 8 hourly periods from now
    hourly_out = []
    for p in hourly_periods[:8]:
        precip = p.get("probabilityOfPrecipitation", {}) or {}
        hourly_out.append({
            "time": p["startTime"][11:16],  # HH:MM
            "temp_f": p["temperature"],
            "conditions": p["shortForecast"],
            "precipitation_chance": precip.get("value") or 0,
        })

    # Current = first hourly period
    cur = hourly_periods[0] if hourly_periods else today_day
    cur_temp_f = cur["temperature"]
    cur_precip = (cur.get("probabilityOfPrecipitation") or {}).get("value") or 0
    wind_val = cur.get("windSpeed", "0 mph").split()[0]
    try:
        wind_mph = int(wind_val)
    except ValueError:
        wind_mph = 0
    wind_dir = cur.get("windDirection", "N")

    conditions_str = cur.get("shortForecast", "Unknown")
    icon_emoji = _conditions_to_emoji(conditions_str)

    return {
        "source": "nws",
        "current": {
            "temp_f": cur_temp_f,
            "temp_c": _f_to_c(cur_temp_f),
            "conditions": conditions_str,
            "wind_mph": wind_mph,
            "wind_direction": wind_dir,
            "precipitation_chance": cur_precip,
            "humidity": None,
            "icon_emoji": icon_emoji,
        },
        "today": {
            "high_f": high_f,
            "low_f": low_f,
            "detailed_forecast": today_day.get("detailedForecast", ""),
        },
        "hourly": hourly_out,
        "alerts": [],
        "fetched_at": _now_iso(),
    }


def _conditions_to_emoji(text: str) -> str:
    """Map a plain-english NWS condition string to an emoji."""
    t = text.lower()
    if "thunder" in t:
        return "⛈️"
    if "snow" in t or "blizzard" in t:
        return "❄️"
    if "fog" in t or "mist" in t:
        return "🌫️"
    if "drizzle" in t:
        return "🌦️"
    if "rain" in t or "shower" in t:
        return "🌧️"
    if "cloud" in t or "overcast" in t:
        return "☁️"
    if "partly" in t or "mostly cloudy" in t:
        return "⛅"
    if "clear" in t or "sunny" in t or "fair" in t:
        return "☀️"
    return "🌡️"


async def _weather_openmeteo() -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=40.7128&longitude=-74.0060"
        "&hourly=temperature_2m,precipitation_probability,precipitation,windspeed_10m,weathercode"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
        "&current_weather=true"
        "&temperature_unit=fahrenheit"
        "&windspeed_unit=mph"
        "&timezone=America%2FNew_York"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    cw = data.get("current_weather", {})
    cur_code = cw.get("weathercode", 0)
    cur_conditions, cur_emoji = _wmo_label(cur_code)
    cur_temp_f = cw.get("temperature", 0)
    wind_mph = cw.get("windspeed", 0)

    daily = data.get("daily", {})
    high_f = (daily.get("temperature_2m_max") or [None])[0]
    low_f = (daily.get("temperature_2m_min") or [None])[0]
    daily_code = (daily.get("weathercode") or [0])[0]
    daily_conditions, _ = _wmo_label(daily_code)

    # Build hourly (next 8 hours)
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    precips = hourly.get("precipitation_probability", [])
    codes = hourly.get("weathercode", [])

    hourly_out = []
    for i in range(min(8, len(times))):
        code_i = codes[i] if i < len(codes) else 0
        cond_i, _ = _wmo_label(code_i)
        hourly_out.append({
            "time": times[i][11:16] if times[i] else "",
            "temp_f": temps[i] if i < len(temps) else cur_temp_f,
            "conditions": cond_i,
            "precipitation_chance": precips[i] if i < len(precips) else 0,
        })

    precip_chance = precips[0] if precips else 0

    return {
        "source": "openmeteo",
        "current": {
            "temp_f": cur_temp_f,
            "temp_c": _f_to_c(cur_temp_f),
            "conditions": cur_conditions,
            "wind_mph": wind_mph,
            "wind_direction": "N/A",
            "precipitation_chance": precip_chance,
            "humidity": None,
            "icon_emoji": cur_emoji,
        },
        "today": {
            "high_f": high_f,
            "low_f": low_f,
            "detailed_forecast": f"{daily_conditions} today. High {high_f}°F, low {low_f}°F.",
        },
        "hourly": hourly_out,
        "alerts": [],
        "fetched_at": _now_iso(),
    }


def _empty_weather(source: str) -> dict:
    return {
        "source": source,
        "current": {
            "temp_f": None, "temp_c": None, "conditions": "Unavailable",
            "wind_mph": None, "wind_direction": None,
            "precipitation_chance": None, "humidity": None, "icon_emoji": "❓",
        },
        "today": {"high_f": None, "low_f": None, "detailed_forecast": "Weather data unavailable."},
        "hourly": [],
        "alerts": [],
        "fetched_at": _now_iso(),
    }


# ── MTA Subway Alerts ─────────────────────────────────────────────────────────

FOCUS_LINES = {"1","2","3","4","5","6","7","A","C","E","B","D","F","M","L","N","Q","R","W","J","Z","G"}


@cached(ttl=900)
async def get_mta_alerts() -> dict:
    try:
        return await _fetch_mta_alerts()
    except Exception as exc:
        print(f"[mta] fetch failed: {exc}", file=sys.stderr)
        return {
            "lines": {},
            "summary": "Transit data temporarily unavailable",
            "error": True,
            "fetched_at": _now_iso(),
        }


async def _fetch_mta_alerts() -> dict:
    url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"
    headers = {**_HEADERS, "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

    entities = data.get("entity", [])
    lines = {}  # type: Dict[str, dict]

    for entity in entities:
        alert = entity.get("alert", {})
        informed = alert.get("informed_entity", [])
        header_translations = (alert.get("header_text") or {}).get("translation", [])
        desc_translations = (alert.get("description_text") or {}).get("translation", [])

        header = next((t["text"] for t in header_translations if t.get("language") == "en"), "")
        description = next((t["text"] for t in desc_translations if t.get("language") == "en"), "")

        affected_routes = {
            ie["route_id"]
            for ie in informed
            if ie.get("route_id") and ie["route_id"].upper() in FOCUS_LINES
        }

        for route in affected_routes:
            route_upper = route.upper()
            if route_upper not in lines:
                lines[route_upper] = {"status": "alerts", "alerts": []}
            lines[route_upper]["alerts"].append({
                "header": header,
                "description": description,
            })
            # Upgrade severity keywords
            lower_header = header.lower()
            if "suspend" in lower_header:
                lines[route_upper]["status"] = "suspended"
            elif "delay" in lower_header and lines[route_upper]["status"] != "suspended":
                lines[route_upper]["status"] = "delays"

    # Lines not in the dict are normal
    for line in FOCUS_LINES:
        if line not in lines:
            lines[line] = {"status": "normal", "alerts": []}

    affected_count = sum(1 for v in lines.values() if v["status"] != "normal")
    if affected_count == 0:
        summary = "All monitored subway lines are operating normally."
    else:
        affected = [k for k, v in lines.items() if v["status"] != "normal"]
        summary = f"{affected_count} line(s) with service issues: {', '.join(sorted(affected))}."

    return {
        "lines": lines,
        "summary": summary,
        "fetched_at": _now_iso(),
    }


# ── Street Closures ───────────────────────────────────────────────────────────

@cached(ttl=900)
async def get_street_closures() -> dict:
    try:
        return await _fetch_street_closures()
    except Exception as exc:
        print(f"[closures] fetch failed: {exc}", file=sys.stderr)
        return {"closures": [], "count": 0, "error": True, "fetched_at": _now_iso()}


async def _fetch_street_closures() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    where_clause = (
        f"startdate <= '{today}T23:59:59.000' AND enddate >= '{today}T00:00:00.000'"
    )
    params = {
        "$limit": "50",
        "$where": where_clause,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://data.cityofnewyork.us/resource/i5rr-er5q.json",
            params=params,
            headers=_HEADERS,
        )
        r.raise_for_status()
        data = r.json()

    closures = []
    for row in data:
        closures.append({
            "on_street": row.get("onstreetname", ""),
            "from_street": row.get("fromstreetname", ""),
            "to_street": row.get("tostreetname", ""),
            "purpose": row.get("purpose", ""),
            "borough": row.get("communityboard", ""),
            "start_date": row.get("startdate", ""),
            "end_date": row.get("enddate", ""),
        })

    return {"closures": closures, "count": len(closures), "fetched_at": _now_iso()}


# ── 311 Complaints ────────────────────────────────────────────────────────────

@cached(ttl=900)
async def get_311_complaints() -> dict:
    try:
        return await _fetch_311_complaints()
    except Exception as exc:
        print(f"[311] fetch failed: {exc}", file=sys.stderr)
        return {"complaints": [], "count": 0, "error": True, "fetched_at": _now_iso()}


async def _fetch_311_complaints() -> dict:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    complaint_types = (
        "'Blocked Driveway','Traffic Signal Condition','Street Condition',"
        "'Pothole','Highway Condition','Street Light Condition'"
    )
    where_clause = (
        f"created_date > '{since}' AND borough = 'MANHATTAN' "
        f"AND complaint_type in({complaint_types})"
    )
    params = {
        "$limit": "100",
        "$where": where_clause,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
            params=params,
            headers=_HEADERS,
        )
        r.raise_for_status()
        data = r.json()

    complaints = []
    for row in data:
        complaints.append({
            "complaint_type": row.get("complaint_type", ""),
            "descriptor": row.get("descriptor", ""),
            "incident_address": row.get("incident_address", ""),
            "created_date": row.get("created_date", ""),
            "status": row.get("status", ""),
        })

    return {"complaints": complaints, "count": len(complaints), "fetched_at": _now_iso()}


# ── Aggregate ─────────────────────────────────────────────────────────────────

async def get_all_conditions() -> dict:
    """Fetch all four data sources concurrently."""
    weather, transit, closures, complaints = await asyncio.gather(
        get_weather(),
        get_mta_alerts(),
        get_street_closures(),
        get_311_complaints(),
    )
    return {
        "weather": weather,
        "transit": transit,
        "closures": closures,
        "complaints_311": complaints,
        "fetched_at": _now_iso(),
    }


def get_demo_conditions() -> dict:
    """Return realistic hardcoded demo data for testing."""
    now = _now_iso()
    today = datetime.now().strftime("%Y-%m-%dT")

    weather = {
        "source": "demo",
        "current": {
            "temp_f": 58,
            "temp_c": 14.4,
            "conditions": "Heavy Rain",
            "wind_mph": 30,
            "wind_direction": "NE",
            "precipitation_chance": 95,
            "humidity": 88,
            "icon_emoji": "🌧️",
        },
        "today": {
            "high_f": 61,
            "low_f": 52,
            "detailed_forecast": (
                "Heavy rain throughout the day, tapering to showers by evening. "
                "Winds northeast 25-35 mph with gusts up to 45 mph. "
                "Temperatures holding in the upper 50s. "
                "Total rainfall accumulation 1.5 to 2.5 inches possible."
            ),
        },
        "hourly": [
            {"time": "09:00", "temp_f": 57, "conditions": "Heavy Rain", "precipitation_chance": 95},
            {"time": "10:00", "temp_f": 57, "conditions": "Heavy Rain", "precipitation_chance": 95},
            {"time": "11:00", "temp_f": 58, "conditions": "Heavy Rain", "precipitation_chance": 90},
            {"time": "12:00", "temp_f": 59, "conditions": "Rain", "precipitation_chance": 85},
            {"time": "13:00", "temp_f": 59, "conditions": "Rain", "precipitation_chance": 80},
            {"time": "14:00", "temp_f": 60, "conditions": "Rain Showers", "precipitation_chance": 75},
            {"time": "15:00", "temp_f": 60, "conditions": "Rain Showers", "precipitation_chance": 70},
            {"time": "16:00", "temp_f": 61, "conditions": "Mostly Cloudy", "precipitation_chance": 50},
        ],
        "alerts": [
            {
                "title": "Wind Advisory",
                "description": "Northeast winds 25 to 35 mph with gusts up to 45 mph. Unsecured objects may be blown around.",
            }
        ],
        "fetched_at": now,
    }

    transit = {
        "lines": {
            "L": {
                "status": "suspended",
                "alerts": [
                    {
                        "header": "L Train Suspended Between 8 Av and Canarsie-Rockaway Pkwy",
                        "description": (
                            "Due to a signal malfunction at Lorimer Street, L train service is suspended "
                            "in both directions. MTA buses are on emergency reroute. Estimated restoration "
                            "time is 2 hours. Customers are advised to use alternate routes."
                        ),
                    }
                ],
            },
            "1": {"status": "normal", "alerts": []},
            "2": {"status": "normal", "alerts": []},
            "3": {"status": "normal", "alerts": []},
            "4": {
                "status": "delays",
                "alerts": [
                    {
                        "header": "4 Train Delays — Weather Related",
                        "description": (
                            "Due to heavy rain conditions, 4 trains are running 10-15 minutes behind schedule. "
                            "Customers should allow extra travel time."
                        ),
                    }
                ],
            },
            "5": {"status": "normal", "alerts": []},
            "6": {"status": "normal", "alerts": []},
            "7": {"status": "normal", "alerts": []},
            "A": {"status": "normal", "alerts": []},
            "C": {"status": "normal", "alerts": []},
            "E": {"status": "normal", "alerts": []},
            "B": {"status": "normal", "alerts": []},
            "D": {"status": "normal", "alerts": []},
            "F": {"status": "normal", "alerts": []},
            "M": {"status": "normal", "alerts": []},
            "N": {"status": "normal", "alerts": []},
            "Q": {"status": "normal", "alerts": []},
            "R": {"status": "normal", "alerts": []},
            "W": {"status": "normal", "alerts": []},
            "J": {"status": "normal", "alerts": []},
            "Z": {"status": "normal", "alerts": []},
            "G": {"status": "normal", "alerts": []},
        },
        "summary": "L train suspended due to signal malfunction. 4 train experiencing weather-related delays.",
        "fetched_at": now,
    }

    closures = {
        "closures": [
            {
                "on_street": "Broadway",
                "from_street": "West 23rd Street",
                "to_street": "West 28th Street",
                "purpose": "Construction — Utility Work",
                "borough": "Manhattan",
                "start_date": today + "07:00:00",
                "end_date": today + "18:00:00",
            },
            {
                "on_street": "8th Avenue",
                "from_street": "West 34th Street",
                "to_street": "West 36th Street",
                "purpose": "Emergency Water Main Repair",
                "borough": "Manhattan",
                "start_date": today + "06:00:00",
                "end_date": today + "20:00:00",
            },
            {
                "on_street": "Delancey Street",
                "from_street": "Essex Street",
                "to_street": "Clinton Street",
                "purpose": "Film Shoot Permit",
                "borough": "Manhattan",
                "start_date": today + "08:00:00",
                "end_date": today + "22:00:00",
            },
        ],
        "count": 3,
        "fetched_at": now,
    }

    complaints_311 = {
        "complaints": [
            {"complaint_type": "Blocked Driveway", "descriptor": "No Access", "incident_address": "123 W 25TH ST", "created_date": today + "06:45:00", "status": "Open"},
            {"complaint_type": "Pothole", "descriptor": "Pothole", "incident_address": "450 BROADWAY", "created_date": today + "07:10:00", "status": "Open"},
            {"complaint_type": "Street Condition", "descriptor": "Flooding", "incident_address": "200 W 14TH ST", "created_date": today + "07:30:00", "status": "Open"},
            {"complaint_type": "Traffic Signal Condition", "descriptor": "Signal Out", "incident_address": "6TH AVE & W 23RD ST", "created_date": today + "07:55:00", "status": "Open"},
            {"complaint_type": "Blocked Driveway", "descriptor": "No Access", "incident_address": "88 FULTON ST", "created_date": today + "08:05:00", "status": "Open"},
            {"complaint_type": "Street Light Condition", "descriptor": "Street Light Out", "incident_address": "300 E 14TH ST", "created_date": today + "08:20:00", "status": "Open"},
            {"complaint_type": "Pothole", "descriptor": "Pothole", "incident_address": "120 VARICK ST", "created_date": today + "08:30:00", "status": "Open"},
            {"complaint_type": "Highway Condition", "descriptor": "Debris on Road", "incident_address": "FDR DRIVE @ E 34TH ST", "created_date": today + "08:45:00", "status": "Open"},
        ],
        "count": 8,
        "fetched_at": now,
    }

    return {
        "weather": weather,
        "transit": transit,
        "closures": closures,
        "complaints_311": complaints_311,
        "fetched_at": now,
    }
