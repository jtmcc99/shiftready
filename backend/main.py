"""
main.py — ShiftReady FastAPI backend
"""

import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Load .env from project root (one level above backend/)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from data_sources import get_all_conditions, get_demo_conditions
from agent import generate_briefing_with_claude
from employees import (
    get_all_employees, get_employee, create_employee, update_employee,
    delete_employee, bulk_upsert_employees, assess_lateness_risk,
    ingest_historical_lateness, get_historical_model_profile, historical_upload_headers,
)

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="ShiftReady API", version="1.0.0")

# ALLOWED_ORIGINS env var lets production add the Vercel frontend URL.
# Defaults to localhost dev ports.
_default_origins = "http://localhost:5173,http://localhost:5174,http://localhost:5175"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BRIEFINGS_DIR = Path("briefings")


@app.on_event("startup")
async def startup():
    BRIEFINGS_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _briefing_filename() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"


def _load_briefing(briefing_id: str) -> dict:
    """Load a briefing JSON file by its stem (filename without .json)."""
    path = BRIEFINGS_DIR / f"{briefing_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Briefing '{briefing_id}' not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _briefing_summary(briefing: dict, briefing_id: str) -> dict:
    """Return the list-view summary of a briefing."""
    alerts = briefing.get("critical_alerts", [])
    return {
        "id": briefing_id,
        "generated_at": briefing.get("generated_at", ""),
        "shift_date": briefing.get("shift_date", ""),
        "overall_status": briefing.get("overall_status", "normal"),
        "executive_summary": briefing.get("executive_summary", ""),
        "demo": briefing.get("demo", False),
        "critical_count": len(alerts),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Helpful landing for reviewers opening the API base URL in a browser."""
    out = {
        "service": "ShiftReady API",
        "health": "/health",
        "docs": "/docs",
    }
    fe = os.getenv("FRONTEND_URL")
    if fe:
        out["frontend_url"] = fe
    return out


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/briefing/generate")
async def generate_briefing(demo: bool = Query(False)):
    """
    Generate a new briefing using live data and Claude.
    The `demo` flag only marks the briefing in history — conditions are
    always fetched live so lateness predictions reflect real transit status.
    """
    conditions = await get_all_conditions()
    briefing = generate_briefing_with_claude(conditions, demo=demo)

    # Persist to disk
    filename = _briefing_filename()
    path = BRIEFINGS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(briefing, f, indent=2, default=str)

    briefing_id = path.stem  # filename without .json
    briefing["id"] = briefing_id
    return briefing


@app.get("/briefing/history")
async def briefing_history():
    """Return list of all briefings, newest first."""
    files = sorted(BRIEFINGS_DIR.glob("*.json"), reverse=True)
    history = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                briefing = json.load(f)
            history.append(_briefing_summary(briefing, path.stem))
        except Exception:
            continue  # Skip corrupt files
    return history


@app.get("/briefing/{briefing_id}")
async def get_briefing(briefing_id: str):
    """Return a specific briefing by its ID (filename stem)."""
    briefing = _load_briefing(briefing_id)
    briefing["id"] = briefing_id
    return briefing


@app.get("/conditions")
async def get_conditions():
    """Return live raw conditions data (weather, transit, closures, 311)."""
    return await get_all_conditions()


# ── Employee endpoints ─────────────────────────────────────────────────────────

@app.get("/employees")
async def list_employees():
    """List all employees."""
    return get_all_employees()


# NOTE: /employees/risk and /employees/template must come BEFORE /employees/{emp_id}
# so FastAPI doesn't try to match the literal strings "risk"/"template" as IDs.

@app.get("/employees/risk")
async def get_lateness_risk():
    """
    Assess lateness risk for all employees using live transit and weather.
    Always uses live data — predictions are based on real MTA alerts.
    """
    employees = get_all_employees()
    conditions = await get_all_conditions()
    return assess_lateness_risk(employees, conditions)


@app.get("/employees/template")
async def download_csv_template():
    """Return a blank CSV template for bulk employee upload."""
    headers = [
        "name", "role", "home_neighborhood", "home_borough",
        "subway_lines", "bus_lines", "commute_mode", "shift_start",
        "zone_assignment", "phone", "email", "notes",
    ]
    example = [
        "Jane Smith", "courier", "Williamsburg", "Brooklyn",
        "L", "B38", "subway", "09:00",
        "East Village", "555-0100", "jane@example.com", "",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerow(example)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shiftready_employees_template.csv"},
    )


@app.get("/employees/history/template")
async def download_history_csv_template():
    """Return a CSV template for historical lateness + indicator uploads."""
    headers = historical_upload_headers()
    example = [
        "", "Jane Smith", "2026-04-14", "09:00", "09:18", "18", "true",
        "delays", "12", "L", "normal", "0", "", "21", "Heavy Rain", "92", "28", "54",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerow(example)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shiftready_historical_lateness_template.csv"},
    )


@app.get("/employees/history/profile")
async def get_history_profile():
    """Return the latest trained historical profile (if available)."""
    profile = get_historical_model_profile()
    return {"profile": profile}


@app.get("/employees/{emp_id}")
async def get_employee_endpoint(emp_id: str):
    emp = get_employee(emp_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


@app.post("/employees")
async def add_employee(data: dict):
    """Add a single employee."""
    if not data.get("name", "").strip():
        raise HTTPException(400, "Employee name is required")
    return create_employee(data)


@app.put("/employees/{emp_id}")
async def update_employee_endpoint(emp_id: str, data: dict):
    """Update an existing employee."""
    emp = update_employee(emp_id, data)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


@app.delete("/employees/{emp_id}")
async def delete_employee_endpoint(emp_id: str):
    """Delete an employee."""
    if not delete_employee(emp_id):
        raise HTTPException(404, "Employee not found")
    return {"deleted": True}


@app.post("/employees/upload")
async def upload_employees(
    file: UploadFile = File(...),
    overwrite: bool = Query(False),
):
    """
    Bulk-upload employees from a CSV or JSON file.
    CSV columns: name, role, home_neighborhood, home_borough, subway_lines,
                 bus_lines, commute_mode, shift_start, zone_assignment, phone, email, notes
    subway_lines and bus_lines are comma-separated within the cell.
    Set overwrite=true to replace all existing employees.
    """
    content = await file.read()
    filename = file.filename or ""

    try:
        if filename.lower().endswith(".json"):
            data_list = json.loads(content)
            if not isinstance(data_list, list):
                raise HTTPException(400, "JSON file must contain an array of employee objects")
        else:
            # Treat as CSV (UTF-8, optional BOM)
            text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            data_list = [dict(row) for row in reader]
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")

    created = bulk_upsert_employees(data_list, overwrite=overwrite)
    return {"uploaded": len(created), "employees": created}


@app.post("/employees/history/upload")
async def upload_historical_data(
    file: UploadFile = File(...),
    overwrite: bool = Query(False),
):
    """
    Bulk-upload historical attendance + signal rows from CSV or JSON.
    The backend learns aggregate signal weights used by /employees/risk.
    """
    content = await file.read()
    filename = file.filename or ""

    try:
        if filename.lower().endswith(".json"):
            data_list = json.loads(content)
            if not isinstance(data_list, list):
                raise HTTPException(400, "JSON file must contain an array of history objects")
        else:
            text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            data_list = [dict(row) for row in reader]
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")

    result = ingest_historical_lateness(data_list, overwrite=overwrite)
    if result.get("uploaded", 0) == 0 and result.get("skipped", 0) > 0:
        raise HTTPException(
            400,
            {
                "message": "No valid rows were uploaded. Check the schema and retry.",
                "rejected_rows": result.get("rejected_rows", []),
            },
        )
    return result
