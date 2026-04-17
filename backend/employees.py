"""
employees.py — Employee storage and commute-based lateness risk assessment.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict
import re

from pydantic import BaseModel, ValidationError, field_validator

EMPLOYEES_FILE = Path("employees.json")
HISTORY_FILE = Path("historical_lateness.json")
HISTORY_PROFILE_FILE = Path("historical_model_profile.json")
TRAIN_DELAY_STATUSES = {"normal", "delays", "suspended"}
BUS_DELAY_STATUSES = {"normal", "delays", "major_delays"}

# ── Storage helpers ────────────────────────────────────────────────────────────

def _load() -> List[dict]:
    if not EMPLOYEES_FILE.exists():
        return []
    with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(employees: List[dict]):
    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(employees, f, indent=2)


def _load_historical_rows() -> List[dict]:
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_historical_rows(rows: List[dict]):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def _load_historical_profile() -> Optional[dict]:
    if not HISTORY_PROFILE_FILE.exists():
        return None
    with open(HISTORY_PROFILE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_historical_profile(profile: dict):
    with open(HISTORY_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


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


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _is_truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "late"}


def _time_to_minutes(value: str) -> Optional[int]:
    if not value:
        return None
    raw = str(value).strip()
    parts = raw.split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return (hour * 60) + minute


def _normalize_train_status(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {"suspended", "suspension", "halted"}:
        return "suspended"
    if value in {"delays", "delay", "major_delays", "major delay"}:
        return "delays"
    return "normal"


def _normalize_bus_status(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {"major", "major_delays", "major delay"}:
        return "major_delays"
    if value in {"delays", "delay"}:
        return "delays"
    return "normal"


def _is_weather_stressful(condition: str, precip_chance: float, wind_mph: float) -> bool:
    c = (condition or "").lower()
    heavy_keywords = ("rain", "snow", "ice", "sleet", "storm", "thunder", "hail", "freezing", "blizzard")
    return precip_chance >= 60 or wind_mph >= 25 or any(k in c for k in heavy_keywords)


class HistoricalLatenessRow(BaseModel):
    employee_id: str = ""
    employee_name: str = ""
    shift_date: str
    scheduled_start: str
    clock_in_time: Optional[str] = ""
    minutes_late: int = 0
    was_late: bool = False
    train_delay_status: str = "normal"
    train_delay_minutes: int = 0
    train_lines_impacted: str = ""
    bus_delay_status: str = "normal"
    bus_delay_minutes: int = 0
    bus_routes_impacted: str = ""
    complaints_311_count: int = 0
    weather_condition: str = ""
    precipitation_chance: float = 0.0
    wind_mph: float = 0.0
    temperature_f: float = 0.0

    @field_validator("employee_id", "employee_name", mode="before")
    @classmethod
    def _strip_name_fields(cls, value):
        return str(value or "").strip()

    @field_validator("shift_date", mode="before")
    @classmethod
    def _valid_shift_date(cls, value):
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("shift_date is required (YYYY-MM-DD)")
        try:
            datetime.strptime(raw, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("shift_date must use YYYY-MM-DD format") from exc
        return raw

    @field_validator("scheduled_start", mode="before")
    @classmethod
    def _valid_scheduled_start(cls, value):
        raw = str(value or "").strip()
        if _time_to_minutes(raw) is None:
            raise ValueError("scheduled_start is required and must be HH:MM")
        return raw

    @field_validator("clock_in_time", mode="before")
    @classmethod
    def _valid_clock_in_time(cls, value):
        raw = str(value or "").strip()
        if raw and _time_to_minutes(raw) is None:
            raise ValueError("clock_in_time must be HH:MM when provided")
        return raw

    @field_validator("train_delay_status", mode="before")
    @classmethod
    def _valid_train_status(cls, value):
        normalized = _normalize_train_status(value)
        if normalized not in TRAIN_DELAY_STATUSES:
            raise ValueError("train_delay_status must be normal, delays, or suspended")
        return normalized

    @field_validator("bus_delay_status", mode="before")
    @classmethod
    def _valid_bus_status(cls, value):
        normalized = _normalize_bus_status(value)
        if normalized not in BUS_DELAY_STATUSES:
            raise ValueError("bus_delay_status must be normal, delays, or major_delays")
        return normalized

    @field_validator("minutes_late", "train_delay_minutes", "bus_delay_minutes", "complaints_311_count", mode="before")
    @classmethod
    def _non_negative_ints(cls, value):
        parsed = _to_int(value, 0)
        if parsed < 0:
            raise ValueError("numeric count fields must be >= 0")
        return parsed

    @field_validator("precipitation_chance", mode="before")
    @classmethod
    def _valid_precip(cls, value):
        parsed = _to_float(value, 0.0)
        if parsed < 0 or parsed > 100:
            raise ValueError("precipitation_chance must be between 0 and 100")
        return parsed

    @field_validator("wind_mph", mode="before")
    @classmethod
    def _valid_wind(cls, value):
        parsed = _to_float(value, 0.0)
        if parsed < 0:
            raise ValueError("wind_mph must be >= 0")
        return parsed

    @field_validator("temperature_f", mode="before")
    @classmethod
    def _valid_temp(cls, value):
        return _to_float(value, 0.0)

    @field_validator("train_lines_impacted", "bus_routes_impacted", "weather_condition", mode="before")
    @classmethod
    def _strip_text_fields(cls, value):
        return str(value or "").strip()


def _parse_route_list(raw: str) -> List[str]:
    if not raw:
        return []
    tokens = re.split(r"[,|;/\s]+", raw)
    cleaned = [t.strip().upper() for t in tokens if t.strip()]
    seen = set()
    unique = []
    for token in cleaned:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique


def _shift_bucket(start_hhmm: str) -> str:
    mins = _time_to_minutes(start_hhmm)
    if mins is None:
        return "unknown"
    if mins < 420:
        return "overnight"
    if mins < 600:
        return "morning_peak"
    if mins < 900:
        return "midday"
    if mins < 1140:
        return "afternoon_evening"
    return "late_night"


def _normalize_history_row(row: dict) -> dict:
    model = HistoricalLatenessRow.model_validate({
        "employee_id": row.get("employee_id", ""),
        "employee_name": row.get("employee_name", ""),
        "shift_date": row.get("shift_date", ""),
        "scheduled_start": row.get("scheduled_start", ""),
        "clock_in_time": row.get("clock_in_time", ""),
        "minutes_late": row.get("minutes_late", 0),
        "was_late": _is_truthy(row.get("was_late", False)),
        "train_delay_status": row.get("train_delay_status", "normal"),
        "train_delay_minutes": row.get("train_delay_minutes", 0),
        "train_lines_impacted": row.get("train_lines_impacted", ""),
        "bus_delay_status": row.get("bus_delay_status", "normal"),
        "bus_delay_minutes": row.get("bus_delay_minutes", 0),
        "bus_routes_impacted": row.get("bus_routes_impacted", ""),
        "complaints_311_count": row.get("complaints_311_count", 0),
        "weather_condition": row.get("weather_condition", ""),
        "precipitation_chance": row.get("precipitation_chance", 0),
        "wind_mph": row.get("wind_mph", 0),
        "temperature_f": row.get("temperature_f", 0),
    })

    if not model.employee_id and not model.employee_name:
        raise ValueError("employee_id or employee_name is required")

    scheduled_min = _time_to_minutes(model.scheduled_start)
    clock_in_min = _time_to_minutes(model.clock_in_time or "")
    minutes_late = model.minutes_late
    if minutes_late == 0 and scheduled_min is not None and clock_in_min is not None:
        minutes_late = max(0, clock_in_min - scheduled_min)

    was_late = bool(model.was_late or minutes_late > 0)
    train_routes = _parse_route_list(model.train_lines_impacted)
    bus_routes = _parse_route_list(model.bus_routes_impacted)
    shift_bucket = _shift_bucket(model.scheduled_start)

    return {
        "employee_id": model.employee_id,
        "employee_name": model.employee_name,
        "shift_date": model.shift_date,
        "scheduled_start": model.scheduled_start,
        "clock_in_time": model.clock_in_time,
        "minutes_late": minutes_late,
        "was_late": was_late,
        "train_delay_status": model.train_delay_status,
        "train_delay_minutes": model.train_delay_minutes,
        "train_lines_impacted": train_routes,
        "bus_delay_status": model.bus_delay_status,
        "bus_delay_minutes": model.bus_delay_minutes,
        "bus_routes_impacted": bus_routes,
        "complaints_311_count": model.complaints_311_count,
        "weather_condition": model.weather_condition,
        "precipitation_chance": model.precipitation_chance,
        "wind_mph": model.wind_mph,
        "temperature_f": model.temperature_f,
        "weather_stressful": _is_weather_stressful(model.weather_condition, model.precipitation_chance, model.wind_mph),
        "shift_bucket": shift_bucket,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _sorted_rows_for_split(rows: List[dict]) -> List[dict]:
    def _sort_key(row):
        raw = row.get("shift_date") or ""
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            dt = datetime.min
        return (dt, row.get("employee_id", ""), row.get("employee_name", ""))

    return sorted(rows, key=_sort_key)


def _build_route_rates(rows: List[dict], key: str) -> List[dict]:
    counters: Dict[str, Dict[str, int]] = {}
    for row in rows:
        for route in row.get(key, []):
            if route not in counters:
                counters[route] = {"samples": 0, "late_count": 0}
            counters[route]["samples"] += 1
            if row.get("was_late"):
                counters[route]["late_count"] += 1
    out = []
    for route, data in counters.items():
        out.append({
            "route": route,
            "samples": data["samples"],
            "late_count": data["late_count"],
            "late_rate": _rate(data["late_count"], data["samples"]),
        })
    out.sort(key=lambda x: x["late_rate"], reverse=True)
    return out


def _build_shift_rates(rows: List[dict]) -> List[dict]:
    counters: Dict[str, Dict[str, int]] = {}
    for row in rows:
        bucket = row.get("shift_bucket", "unknown")
        if bucket not in counters:
            counters[bucket] = {"samples": 0, "late_count": 0}
        counters[bucket]["samples"] += 1
        if row.get("was_late"):
            counters[bucket]["late_count"] += 1
    out = []
    for bucket, data in counters.items():
        out.append({
            "bucket": bucket,
            "samples": data["samples"],
            "late_count": data["late_count"],
            "late_rate": _rate(data["late_count"], data["samples"]),
        })
    out.sort(key=lambda x: x["bucket"])
    return out


def _predict_row_risk_score(row: dict, profile: dict) -> int:
    baseline_late_rate = _to_float(profile.get("baseline_late_rate"), 0.0)
    feature_rates = profile.get("feature_rates", {})
    risk_score = 0

    train_status = row.get("train_delay_status", "normal")
    bus_status = row.get("bus_delay_status", "normal")
    if train_status == "suspended":
        risk_score += 65
    elif train_status == "delays":
        risk_score += 28

    if bus_status == "major_delays":
        risk_score += 30
    elif bus_status == "delays":
        risk_score += 16

    if row.get("weather_stressful"):
        risk_score += 12
    if _to_int(row.get("complaints_311_count"), 0) >= 15:
        risk_score += 10

    train_feature_delta = max(0.0, _to_float(feature_rates.get("train_issue_late_rate"), 0.0) - baseline_late_rate)
    if train_status in {"delays", "suspended"} and train_feature_delta > 0:
        risk_score += min(18, round(train_feature_delta * 45))

    bus_feature_delta = max(0.0, _to_float(feature_rates.get("bus_issue_late_rate"), 0.0) - baseline_late_rate)
    if bus_status in {"delays", "major_delays"} and bus_feature_delta > 0:
        risk_score += min(14, round(bus_feature_delta * 40))

    weather_feature_delta = max(0.0, _to_float(feature_rates.get("stressful_weather_late_rate"), 0.0) - baseline_late_rate)
    if row.get("weather_stressful") and weather_feature_delta > 0:
        risk_score += min(12, round(weather_feature_delta * 35))

    complaints_feature_delta = max(0.0, _to_float(feature_rates.get("high_311_late_rate"), 0.0) - baseline_late_rate)
    if _to_int(row.get("complaints_311_count"), 0) >= 15 and complaints_feature_delta > 0:
        risk_score += min(10, round(complaints_feature_delta * 30))

    shift_rates = profile.get("shift_bucket_rates", [])
    shift_map = {s.get("bucket"): s for s in shift_rates}
    shift_bucket = row.get("shift_bucket", "unknown")
    shift_data = shift_map.get(shift_bucket)
    if shift_data and _to_int(shift_data.get("samples"), 0) >= 8:
        shift_delta = max(0.0, _to_float(shift_data.get("late_rate"), 0.0) - baseline_late_rate)
        if shift_delta > 0:
            risk_score += min(8, round(shift_delta * 30))

    route_scores = profile.get("route_rates", {})
    train_route_map = {r.get("route"): r for r in route_scores.get("train_lines", [])}
    bus_route_map = {r.get("route"): r for r in route_scores.get("bus_routes", [])}
    route_bonus = 0
    for line in row.get("train_lines_impacted", []):
        route = train_route_map.get(line)
        if route and _to_int(route.get("samples"), 0) >= 5:
            route_delta = max(0.0, _to_float(route.get("late_rate"), 0.0) - baseline_late_rate)
            route_bonus = max(route_bonus, min(10, round(route_delta * 35)))
    for bus in row.get("bus_routes_impacted", []):
        route = bus_route_map.get(bus)
        if route and _to_int(route.get("samples"), 0) >= 5:
            route_delta = max(0.0, _to_float(route.get("late_rate"), 0.0) - baseline_late_rate)
            route_bonus = max(route_bonus, min(8, round(route_delta * 30)))
    risk_score += route_bonus
    return risk_score


def _classification_metrics(rows: List[dict], profile: dict) -> dict:
    if not rows:
        return {
            "samples": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "threshold": 30,
        }

    tp = fp = tn = fn = 0
    for row in rows:
        predicted_late = _predict_row_risk_score(row, profile) >= 30
        actual_late = bool(row.get("was_late"))
        if predicted_late and actual_late:
            tp += 1
        elif predicted_late and not actual_late:
            fp += 1
        elif not predicted_late and not actual_late:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    accuracy = _rate(tp + tn, total)
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    f1 = 0.0
    if (precision + recall) > 0:
        f1 = round((2 * precision * recall) / (precision + recall), 4)

    return {
        "samples": total,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "threshold": 30,
    }


def _build_historical_profile(rows: List[dict]) -> dict:
    total_rows = len(rows)
    late_count = sum(1 for r in rows if r.get("was_late"))
    baseline = _rate(late_count, total_rows)

    train_issue_rows = [r for r in rows if r.get("train_delay_status") in {"delays", "suspended"}]
    bus_issue_rows = [r for r in rows if r.get("bus_delay_status") in {"delays", "major_delays"}]
    high_311_rows = [r for r in rows if _to_int(r.get("complaints_311_count"), 0) >= 15]
    weather_rows = [r for r in rows if r.get("weather_stressful")]

    train_issue_late = sum(1 for r in train_issue_rows if r.get("was_late"))
    bus_issue_late = sum(1 for r in bus_issue_rows if r.get("was_late"))
    high_311_late = sum(1 for r in high_311_rows if r.get("was_late"))
    weather_late = sum(1 for r in weather_rows if r.get("was_late"))

    employees = {}
    for row in rows:
        key = row.get("employee_id") or row.get("employee_name")
        if not key:
            continue
        if key not in employees:
            employees[key] = {
                "employee_key": key,
                "employee_name": row.get("employee_name", ""),
                "samples": 0,
                "late_count": 0,
            }
        employees[key]["samples"] += 1
        if row.get("was_late"):
            employees[key]["late_count"] += 1

    for item in employees.values():
        item["baseline_late_rate"] = _rate(item["late_count"], item["samples"])

    profile = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "records": total_rows,
        "baseline_late_rate": baseline,
        "feature_rates": {
            "train_issue_late_rate": _rate(train_issue_late, len(train_issue_rows)),
            "bus_issue_late_rate": _rate(bus_issue_late, len(bus_issue_rows)),
            "high_311_late_rate": _rate(high_311_late, len(high_311_rows)),
            "stressful_weather_late_rate": _rate(weather_late, len(weather_rows)),
        },
        "feature_samples": {
            "train_issue_samples": len(train_issue_rows),
            "bus_issue_samples": len(bus_issue_rows),
            "high_311_samples": len(high_311_rows),
            "stressful_weather_samples": len(weather_rows),
        },
        "route_rates": {
            "train_lines": _build_route_rates(rows, "train_lines_impacted"),
            "bus_routes": _build_route_rates(rows, "bus_routes_impacted"),
        },
        "shift_bucket_rates": _build_shift_rates(rows),
        "employees": list(employees.values()),
    }
    return profile


def get_historical_model_profile() -> Optional[dict]:
    return _load_historical_profile()


def ingest_historical_lateness(rows: List[dict], overwrite: bool = False) -> dict:
    normalized = []
    rejected = []
    for idx, row in enumerate(rows):
        try:
            parsed = _normalize_history_row(row)
            normalized.append(parsed)
        except (ValidationError, ValueError) as exc:
            rejected.append({
                "row_index": idx,
                "reason": str(exc),
                "row": row,
            })

    existing = [] if overwrite else _load_historical_rows()
    merged = existing + normalized
    _save_historical_rows(merged)

    profile = _build_historical_profile(merged)
    split_source = _sorted_rows_for_split(merged)
    split_at = int(len(split_source) * 0.8)
    if len(split_source) >= 10:
        train_rows = split_source[:split_at]
        test_rows = split_source[split_at:]
    else:
        train_rows = split_source
        test_rows = []

    training_profile = _build_historical_profile(train_rows) if train_rows else _build_historical_profile(merged)
    profile["model_metrics"] = {
        "train": _classification_metrics(train_rows, training_profile),
        "test": _classification_metrics(test_rows, training_profile),
        "split": {
            "strategy": "chronological_80_20",
            "train_samples": len(train_rows),
            "test_samples": len(test_rows),
        },
    }
    _save_historical_profile(profile)

    return {
        "uploaded": len(normalized),
        "skipped": len(rejected),
        "rejected_rows": rejected[:25],
        "total_records": len(merged),
        "profile": profile,
    }


def historical_upload_headers() -> List[str]:
    return [
        "employee_id",
        "employee_name",
        "shift_date",
        "scheduled_start",
        "clock_in_time",
        "minutes_late",
        "was_late",
        "train_delay_status",
        "train_delay_minutes",
        "train_lines_impacted",
        "bus_delay_status",
        "bus_delay_minutes",
        "bus_routes_impacted",
        "complaints_311_count",
        "weather_condition",
        "precipitation_chance",
        "wind_mph",
        "temperature_f",
    ]


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
    historical_profile = _load_historical_profile()
    baseline_late_rate = _to_float((historical_profile or {}).get("baseline_late_rate"), default=0.0)
    feature_rates = (historical_profile or {}).get("feature_rates", {})
    route_rates = (historical_profile or {}).get("route_rates", {})
    shift_bucket_rates = (historical_profile or {}).get("shift_bucket_rates", [])
    train_route_map = {r.get("route"): r for r in route_rates.get("train_lines", [])}
    bus_route_map = {r.get("route"): r for r in route_rates.get("bus_routes", [])}
    shift_bucket_map = {r.get("bucket"): r for r in shift_bucket_rates}
    employee_baseline = {}
    if historical_profile:
        for row in historical_profile.get("employees", []):
            key = row.get("employee_key")
            if key:
                employee_baseline[key] = {
                    "rate": _to_float(row.get("baseline_late_rate"), 0.0),
                    "samples": _to_int(row.get("samples"), 0),
                }
    complaints_311_count = _to_int((conditions.get("complaints_311") or {}).get("count"), 0)

    for emp in employees:
        risk_score = 0
        risk_reasons: List[str] = []
        model_signals: List[str] = []
        affected_lines: List[str] = []
        estimated_delay_min = 0
        mode = (emp.get("commute_mode") or "subway").lower()
        shift_bucket = _shift_bucket(emp.get("shift_start") or "")

        for line in emp.get("subway_lines", []):
            line_data = transit_lines.get(line, {})
            status = line_data.get("status", "normal")

            if status == "suspended":
                risk_score += 65
                affected_lines.append(line)
                estimated_delay_min = max(estimated_delay_min, 40)
                risk_reasons.append(f"{line} train suspended")
            elif status in ("delays", "major_delays", "delay"):
                risk_score += 28
                affected_lines.append(line)
                estimated_delay_min = max(estimated_delay_min, 20)
                risk_reasons.append(f"{line} train delays")
            elif status == "planned_work":
                risk_score += 15
                affected_lines.append(line)
                estimated_delay_min = max(estimated_delay_min, 15)
                risk_reasons.append(f"{line} planned service work")

        # Bike/walk in bad weather
        if mode in ("bike", "bicycle", "cycling", "walk", "walking") and bad_bike_weather:
            risk_score += 24
            estimated_delay_min = max(estimated_delay_min, 20)
            weather_desc = current.get("conditions", "adverse weather")
            risk_reasons.append(f"{mode.capitalize()} commuter in {weather_desc}")

        # Historical profile adjustments
        if historical_profile:
            emp_key = emp.get("id") or ""
            emp_name = emp.get("name") or ""
            person_history = employee_baseline.get(emp_key) or employee_baseline.get(emp_name)
            if person_history and person_history.get("samples", 0) >= 3:
                personal_rate = person_history["rate"]
                if personal_rate > baseline_late_rate:
                    delta = max(0.0, personal_rate - baseline_late_rate)
                    bonus = min(20, round(delta * 60))
                    if bonus > 0:
                        risk_score += bonus
                        model_signals.append(
                            f"historically late {round(personal_rate * 100)}% of shifts ({person_history['samples']} samples)"
                        )

            train_feature_delta = max(0.0, _to_float(feature_rates.get("train_issue_late_rate"), 0.0) - baseline_late_rate)
            if affected_lines and train_feature_delta > 0:
                bonus = min(18, round(train_feature_delta * 45))
                if bonus > 0:
                    risk_score += bonus
                    model_signals.append("historical train-disruption signal")

            for line in affected_lines:
                route = train_route_map.get(str(line).upper())
                if route and _to_int(route.get("samples"), 0) >= 5:
                    route_delta = max(0.0, _to_float(route.get("late_rate"), 0.0) - baseline_late_rate)
                    bonus = min(10, round(route_delta * 35))
                    if bonus > 0:
                        risk_score += bonus
                        model_signals.append(f"historical pattern on {line} line")
                        break

            for bus in emp.get("bus_lines", []):
                route = bus_route_map.get(str(bus).upper())
                if route and _to_int(route.get("samples"), 0) >= 5:
                    route_delta = max(0.0, _to_float(route.get("late_rate"), 0.0) - baseline_late_rate)
                    bonus = min(8, round(route_delta * 30))
                    if bonus > 0:
                        risk_score += bonus
                        model_signals.append(f"historical pattern on bus {bus}")
                        break

            weather_stressful_now = _is_weather_stressful(cond_str, precip_chance, wind_mph)
            weather_feature_delta = max(0.0, _to_float(feature_rates.get("stressful_weather_late_rate"), 0.0) - baseline_late_rate)
            if weather_stressful_now and weather_feature_delta > 0:
                bonus = min(12, round(weather_feature_delta * 35))
                if bonus > 0:
                    risk_score += bonus
                    model_signals.append("historical weather signal")

            high_311_now = complaints_311_count >= 15
            complaints_feature_delta = max(0.0, _to_float(feature_rates.get("high_311_late_rate"), 0.0) - baseline_late_rate)
            if high_311_now and complaints_feature_delta > 0:
                bonus = min(10, round(complaints_feature_delta * 30))
                if bonus > 0:
                    risk_score += bonus
                    model_signals.append("historical 311 congestion signal")

            shift_data = shift_bucket_map.get(shift_bucket)
            if shift_data and _to_int(shift_data.get("samples"), 0) >= 8:
                shift_delta = max(0.0, _to_float(shift_data.get("late_rate"), 0.0) - baseline_late_rate)
                bonus = min(8, round(shift_delta * 30))
                if bonus > 0:
                    risk_score += bonus
                    model_signals.append(f"historically higher lateness in {shift_bucket} shifts")

        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "moderate"
        else:
            risk_level = "low"

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
            "risk_score": risk_score,
            "model_signals": model_signals,
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
        "model_info": {
            "historical_model_enabled": bool(historical_profile),
            "historical_records": _to_int((historical_profile or {}).get("records"), 0),
            "historical_trained_at": (historical_profile or {}).get("trained_at"),
            "metrics": (historical_profile or {}).get("model_metrics", {}),
            "feature_samples": (historical_profile or {}).get("feature_samples", {}),
            "route_coverage": {
                "train_lines": len(((historical_profile or {}).get("route_rates", {}) or {}).get("train_lines", [])),
                "bus_routes": len(((historical_profile or {}).get("route_rates", {}) or {}).get("bus_routes", [])),
            },
            "shift_bucket_coverage": len((historical_profile or {}).get("shift_bucket_rates", [])),
        },
        "employees": results,
    }
