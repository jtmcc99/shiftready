"""
employees.py — Employee storage and commute-based lateness risk assessment.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict

EMPLOYEES_FILE = Path("employees.json")

# ── Storage helpers ────────────────────────────────────────────────────────────

def _load() -> List[dict]:
    if not EMPLOYEES_FILE.exists():
        return []
    with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(employees: List[dict]):
    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(employees, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_all_employees() -> List[dict]:
    return _load()


def get_employee(emp_id: str) -> Optional[dict]:
    return next((e for e in _load() if e["id"] == emp_id), None)


def create_employee(data: dict) -> dict:
    employees = _load()
    emp = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": data.get("name", "").strip(),
        "role": data.get("role", "courier").strip(),
        "home_neighborhood": data.get("home_neighborhood", "").strip(),
        "home_borough": data.get("home_borough", "").strip(),
        "subway_lines": data.get("subway_lines", []),
        "bus_lines": data.get("bus_lines", []),
        "commute_mode": data.get("commute_mode", "subway").strip(),
        "shift_start": data.get("shift_start", "09:00").strip(),
        "zone_assignment": data.get("zone_assignment", "").strip(),
        "phone": data.get("phone", "").strip(),
        "email": data.get("email", "").strip(),
        "notes": data.get("notes", "").strip(),
    }
    employees.append(emp)
    _save(employees)
    return emp


def update_employee(emp_id: str, data: dict) -> Optional[dict]:
    employees = _load()
    for i, emp in enumerate(employees):
        if emp["id"] == emp_id:
            updated = {**emp, **data, "id": emp_id, "created_at": emp["created_at"]}
            employees[i] = updated
            _save(employees)
            return updated
    return None


def delete_employee(emp_id: str) -> bool:
    employees = _load()
    filtered = [e for e in employees if e["id"] != emp_id]
    if len(filtered) == len(employees):
        return False
    _save(filtered)
    return True


def bulk_upsert_employees(data_list: List[dict], overwrite: bool = False) -> List[dict]:
    """Add multiple employees. If overwrite=True, replaces all existing."""
    existing = [] if overwrite else _load()
    created = []
    for data in data_list:
        emp = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": data.get("name", "").strip(),
            "role": data.get("role", "courier").strip(),
            "home_neighborhood": data.get("home_neighborhood", "").strip(),
            "home_borough": data.get("home_borough", "").strip(),
            "subway_lines": _parse_list(data.get("subway_lines", [])),
            "bus_lines": _parse_list(data.get("bus_lines", [])),
            "commute_mode": data.get("commute_mode", "subway").strip(),
            "shift_start": data.get("shift_start", "09:00").strip(),
            "zone_assignment": data.get("zone_assignment", "").strip(),
            "phone": data.get("phone", "").strip(),
            "email": data.get("email", "").strip(),
            "notes": data.get("notes", "").strip(),
        }
        if emp["name"]:
            existing.append(emp)
            created.append(emp)
    _save(existing)
    return created


def _parse_list(value) -> List[str]:
    """Accept a list, or a comma-separated string."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ── Lateness risk assessment ───────────────────────────────────────────────────

# Which subway lines serve which zones (for explanation text)
LINE_ZONE_MAP = {
    "L":   ["East Village", "Williamsburg"],
    "1":   ["Chelsea", "Downtown", "Uptown West"],
    "2":   ["Chelsea", "Downtown", "Uptown West"],
    "3":   ["Chelsea", "Downtown", "Uptown West"],
    "4":   ["East Village", "Midtown East", "Uptown East"],
    "5":   ["East Village", "Midtown East", "Uptown East"],
    "6":   ["East Village", "Midtown East", "Uptown East"],
    "A":   ["Chelsea", "Midtown West"],
    "C":   ["Chelsea", "Midtown West"],
    "E":   ["Chelsea", "Midtown West"],
    "B":   ["Midtown", "Downtown"],
    "D":   ["Midtown", "Downtown"],
    "F":   ["Midtown", "Downtown"],
    "M":   ["Midtown", "Downtown"],
    "N":   ["Midtown", "Downtown"],
    "Q":   ["Midtown", "Downtown"],
    "R":   ["Midtown", "Downtown"],
    "W":   ["Midtown", "Downtown"],
    "J":   ["Downtown"],
    "Z":   ["Downtown"],
    "G":   ["Brooklyn/Queens"],
    "7":   ["Midtown", "Queens"],
}

BAD_WEATHER_FOR_BIKES = {"snow", "ice", "sleet", "blizzard", "freezing", "hail"}


def assess_lateness_risk(employees: List[dict], conditions: dict) -> dict:
    """
    Rule-based per-employee lateness risk. Crosses commute data against
    live transit alerts and weather.
    """
    transit = conditions.get("transit", {})
    transit_lines = transit.get("lines", {})  # {line_id: {status, alerts:[...]}}
    transit_error = transit.get("error", False)

    weather = conditions.get("weather", {})
    current = weather.get("current", {})
    wind_mph = float(current.get("wind_mph") or 0)
    temp_f = float(current.get("temp_f") or 65)
    precip_chance = float(current.get("precipitation_chance") or 0)
    cond_str = (current.get("conditions") or "").lower()

    bad_bike_weather = (
        wind_mph > 25
        or precip_chance > 60
        or temp_f < 20
        or temp_f > 95
        or any(w in cond_str for w in BAD_WEATHER_FOR_BIKES)
    )

    RISK_ORDER = {"high": 0, "moderate": 1, "low": 2}
    results = []

    for emp in employees:
        risk_level = "low"
        risk_reasons: List[str] = []
        affected_lines: List[str] = []
        estimated_delay_min = 0
        mode = (emp.get("commute_mode") or "subway").lower()

        for line in emp.get("subway_lines", []):
            line_data = transit_lines.get(line, {})
            status = line_data.get("status", "normal")

            if status == "suspended":
                risk_level = "high"
                affected_lines.append(line)
                estimated_delay_min = max(estimated_delay_min, 40)
                risk_reasons.append(f"{line} train suspended")
            elif status in ("delays", "major_delays", "delay"):
                if risk_level != "high":
                    risk_level = "moderate"
                affected_lines.append(line)
                estimated_delay_min = max(estimated_delay_min, 20)
                risk_reasons.append(f"{line} train delays")
            elif status == "planned_work":
                if risk_level == "low":
                    risk_level = "moderate"
                affected_lines.append(line)
                estimated_delay_min = max(estimated_delay_min, 15)
                risk_reasons.append(f"{line} planned service work")

        # Bike/walk in bad weather
        if mode in ("bike", "bicycle", "cycling", "walk", "walking") and bad_bike_weather:
            if risk_level == "low":
                risk_level = "moderate"
            estimated_delay_min = max(estimated_delay_min, 20)
            weather_desc = current.get("conditions", "adverse weather")
            risk_reasons.append(f"{mode.capitalize()} commuter in {weather_desc}")

        recommendation = ""
        if risk_level == "high":
            recommendation = "Contact immediately — confirm ETA or arrange backup"
        elif risk_level == "moderate":
            recommendation = "Send heads-up; ask for ETA confirmation"

        results.append({
            "id": emp["id"],
            "name": emp["name"],
            "role": emp.get("role", ""),
            "phone": emp.get("phone", ""),
            "email": emp.get("email", ""),
            "home_neighborhood": emp.get("home_neighborhood", ""),
            "home_borough": emp.get("home_borough", ""),
            "subway_lines": emp.get("subway_lines", []),
            "bus_lines": emp.get("bus_lines", []),
            "commute_mode": mode,
            "shift_start": emp.get("shift_start", ""),
            "zone_assignment": emp.get("zone_assignment", ""),
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
            "affected_lines": affected_lines,
            "estimated_delay_min": estimated_delay_min,
            "recommendation": recommendation,
        })

    results.sort(key=lambda x: RISK_ORDER[x["risk_level"]])

    high_count = sum(1 for r in results if r["risk_level"] == "high")
    moderate_count = sum(1 for r in results if r["risk_level"] == "moderate")
    total = len(results)

    overall_risk = "low"
    if high_count:
        overall_risk = "high"
    elif moderate_count:
        overall_risk = "moderate"

    if not results:
        summary = "No employees on file. Add employee commute data to enable lateness predictions."
    elif high_count == 0 and moderate_count == 0:
        summary = f"All {total} employee{'s' if total != 1 else ''} appear on-time based on current conditions."
    else:
        parts = []
        if high_count:
            parts.append(f"{high_count} high-risk")
        if moderate_count:
            parts.append(f"{moderate_count} at moderate risk")
        summary = f"{' and '.join(parts)} of {total} employees may be delayed by current conditions."

    data_note = "Transit data unavailable — risk assessment based on weather only." if transit_error else None

    return {
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "overall_risk": overall_risk,
        "total_employees": total,
        "high_risk_count": high_count,
        "moderate_risk_count": moderate_count,
        "at_risk_count": high_count + moderate_count,
        "summary": summary,
        "data_note": data_note,
        "employees": results,
    }
