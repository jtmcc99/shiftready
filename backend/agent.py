"""
agent.py — Use Claude to generate a structured ops briefing from conditions data.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

import anthropic
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

_client = None  # type: Optional[anthropic.Anthropic]


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in environment / .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior operations manager for ShiftReady, a delivery logistics company operating in New York City. Your job is to write a concise, actionable morning shift briefing for delivery managers.

## DELIVERY ZONES

- **Uptown**: Above 59th Street
- **Midtown**: 34th–59th Street
  Key transit lines: N/Q/R/W, 4/5/6, A/C/E, B/D/F/M, 7
- **Chelsea**: 14th–34th Street
  Key transit lines: 1/2/3, A/C/E, L
- **East Village**: Below 14th Street, East of Broadway
  Key transit lines: L, 4/5/6, J/Z
- **Downtown/FiDi**: Below 14th Street, West of Broadway
  Key transit lines: 1/2/3, A/C/E, J/Z, R/W

## SUBWAY → ZONE MAPPING

- **L**: East Village, Williamsburg (staff commuting from Brooklyn)
- **1/2/3**: Chelsea, Downtown West, Uptown West
- **4/5/6**: East Village, Midtown East, Uptown East
- **A/C/E**: Chelsea, Midtown West
- **B/D/F/M**: Midtown, Downtown
- **N/Q/R/W**: Midtown, Downtown
- **J/Z**: Downtown/FiDi

## WEATHER → OPERATIONAL RULES

- **Rain / Drizzle**: Expect 25–40% longer delivery times. Reduce courier capacity. Add driver coverage.
- **Snow / Ice**: Driver-only deliveries. Cancel all bike/scooter dispatches immediately.
- **Extreme heat (>90°F)**: Flag perishables for priority dispatch. Mandate hydration breaks. Check cooler bag compliance.
- **Extreme cold (<20°F)**: Bikes significantly slower. Watch for black ice. Pre-warm vehicles.
- **High wind (>25 mph)**: Reassign all bike deliveries to drivers. Secure cargo in trucks.

## TRANSIT → STAFFING RULES

- **Suspended line**: Staff depending on that line may be 20–40 minutes late. Dispatch delayed accordingly OR call backup staff. Issue zone alert.
- **Major delays**: Staff may be 10–20 minutes late. Adjust dispatch windows.
- **Planned weekend work**: Advance warning issued. Rerouting available. Alert affected couriers.

## YOUR TASK

Analyze the provided conditions data and write a structured JSON briefing. Be specific, actionable, and direct. Delivery managers are busy — every recommendation must have a clear action they can take in the next 30 minutes.

**You must return ONLY valid JSON — no markdown fences, no explanation text, nothing before or after the JSON object.**
"""


def _build_user_message(conditions: dict) -> str:
    today = datetime.now().strftime("%A, %B %d %Y")
    return f"""Today is {today}.

Here is the current operational conditions data for New York City:

{json.dumps(conditions, indent=2, default=str)}

Based on this data, generate a complete morning shift briefing following the JSON structure specified. Be specific about which zones, lines, and streets are affected. Make every recommendation actionable with clear steps. If data is missing or unavailable for a source, note it in data_quality and still produce the best briefing you can from available data.

Remember: return ONLY the JSON object, nothing else."""


_RESPONSE_SCHEMA = {
    "generated_at": "ISO timestamp",
    "demo": False,
    "shift_date": "Day, Month DD YYYY",
    "overall_status": "normal|moderate_alert|high_alert",
    "executive_summary": "...",
    "critical_alerts": [
        {
            "id": "alert_001",
            "severity": "critical|warning|info",
            "category": "weather|transit|route|combined",
            "title": "...",
            "description": "...",
            "impact": "...",
            "action": "...",
        }
    ],
    "weather_impact": {
        "current_temp_f": 0,
        "conditions": "...",
        "icon": "...",
        "wind_mph": 0,
        "precipitation_chance": 0,
        "severity": "low|moderate|high|critical",
        "forecast_summary": "...",
        "operational_impacts": [],
        "hourly_outlook": [{"hour": "9 AM", "conditions": "...", "temp_f": 0, "precip_chance": 0}],
    },
    "transit_status": {
        "overall_severity": "normal|moderate|severe",
        "lines": [
            {
                "line": "L",
                "status": "suspended|delays|normal|planned_work",
                "description": "...",
                "zones_affected": [],
                "staffing_impact": "...",
            }
        ],
        "lines_normal": [],
        "summary": "...",
    },
    "route_disruptions": [
        {
            "id": "route_001",
            "location": "...",
            "type": "construction|closure|event|pothole",
            "zones_affected": [],
            "impact": "...",
            "recommendation": "...",
            "severity": "low|moderate|high",
        }
    ],
    "recommendations": [
        {
            "priority": 1,
            "action": "...",
            "reason": "...",
            "zone": "...",
        }
    ],
    "data_quality": {
        "weather_source": "nws|openmeteo|demo|unavailable",
        "transit_available": True,
        "closures_available": True,
        "complaints_available": True,
    },
}


def generate_briefing_with_claude(conditions: dict, demo: bool = False) -> dict:
    """
    Send conditions data to Claude and get back a structured ops briefing.
    Returns a dict matching the briefing schema.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        client = _get_client()
    except RuntimeError as exc:
        return _error_briefing(str(exc), demo, now_iso)

    schema_note = (
        "The briefing MUST conform to this exact JSON structure:\n"
        + json.dumps(_RESPONSE_SCHEMA, indent=2)
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT + "\n\n" + schema_note,
            messages=[
                {"role": "user", "content": _build_user_message(conditions)}
            ],
        )
    except Exception as exc:
        return _error_briefing(str(exc), demo, now_iso)

    raw_text = response.content[0].text.strip()

    # Strip accidental markdown fences
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        briefing = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return _error_briefing(f"JSON parse error: {exc}", demo, now_iso)

    briefing["demo"] = demo
    briefing["generated_at"] = now_iso
    return briefing


def _error_briefing(error_msg: str, demo: bool, now_iso: str) -> dict:
    """Return a minimal valid briefing when Claude fails."""
    today = datetime.now().strftime("%A, %B %d %Y")
    return {
        "generated_at": now_iso,
        "demo": demo,
        "shift_date": today,
        "overall_status": "moderate_alert",
        "executive_summary": (
            f"Briefing generation encountered an error: {error_msg}. "
            "Please check the backend logs and retry. "
            "Manual review of conditions data is recommended."
        ),
        "critical_alerts": [
            {
                "id": "error_001",
                "severity": "warning",
                "category": "combined",
                "title": "Briefing Generation Failed",
                "description": f"Claude could not generate a briefing: {error_msg}",
                "impact": "No automated analysis available — review conditions data manually.",
                "action": "Verify ANTHROPIC_API_KEY is configured on the server and retry.",
            }
        ],
        "weather_impact": {
            "current_temp_f": None,
            "conditions": "Unknown — check raw conditions",
            "icon": "❓",
            "wind_mph": None,
            "precipitation_chance": None,
            "severity": "low",
            "forecast_summary": "Weather data was fetched but briefing generation failed.",
            "operational_impacts": ["Review conditions tab for raw data"],
            "hourly_outlook": [],
        },
        "transit_status": {
            "overall_severity": "normal",
            "lines": [],
            "lines_normal": [],
            "summary": "Review conditions tab for raw transit data.",
        },
        "route_disruptions": [],
        "recommendations": [
            {
                "priority": 1,
                "action": "Retry briefing generation",
                "reason": "Automated analysis failed — a retry may succeed",
                "zone": "All",
            }
        ],
        "data_quality": {
            "weather_source": "unavailable",
            "transit_available": False,
            "closures_available": False,
            "complaints_available": False,
        },
    }
