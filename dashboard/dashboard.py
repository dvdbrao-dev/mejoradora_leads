#!/usr/bin/env python3
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = BASE_DIR / "runs"
PLANTS_FILE = BASE_DIR / "data" / "plants.json"
STATUS_FILE = RUNS_DIR / "lead_status.json"
CUSTOM_SEARCH_HISTORY_FILE = RUNS_DIR / "custom_searches.json"
DASHBOARD_DIR = BASE_DIR / "dashboard"
SCRAPER_CUSTOM_ZONE = BASE_DIR / "scripts" / "scraper_custom_zone.py"
INGEST_SCRIPT = BASE_DIR / "scripts" / "ingest.py"

app = FastAPI(title="Openfang Dashboard", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatusUpdate(BaseModel):
    status: str


class CustomZoneSearchPayload(BaseModel):
    lat: float
    lng: float
    radius_km: float = 2.0
    plant_id: str | None = None
    zone_type: str | None = None


class IngestCustomPayload(BaseModel):
    csv_path: str


VALID_STATUSES = {"pendiente", "contactado", "cerrado", "no_interesa"}


def parse_json_file(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_tier(raw_tier: Any, status: str) -> str:
    tier = str(raw_tier or "").upper().strip()
    if tier in {"A", "B", "C", "DISCARD"}:
        return tier
    if status == "descartado_por_paco":
        return "DISCARD"
    return "C"


def load_status_overrides() -> dict[str, str]:
    data = parse_json_file(STATUS_FILE)
    return data if isinstance(data, dict) else {}


def save_status_overrides(statuses: dict[str, str]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with STATUS_FILE.open("w", encoding="utf-8") as f:
        json.dump(statuses, f, ensure_ascii=False, indent=2)


def extract_messages(manolo: Any) -> list[dict[str, Any]]:
    if isinstance(manolo, list):
        items = manolo
    elif isinstance(manolo, dict):
        items = [manolo]
    else:
        items = []

    output = []
    for item in items:
        if not isinstance(item, dict):
            continue
        output.append(
            {
                "variant": item.get("variant", ""),
                "message": item.get("message", ""),
                "cta": item.get("cta", ""),
            }
        )
    return output


def load_leads() -> list[dict[str, Any]]:
    status_overrides = load_status_overrides()
    leads: list[dict[str, Any]] = []

    for run_file in RUNS_DIR.glob("*.json"):
        if run_file.name in {STATUS_FILE.name, CUSTOM_SEARCH_HISTORY_FILE.name}:
            continue

        run = parse_json_file(run_file)
        if not isinstance(run, dict):
            continue

        lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
        lead_id = str(run.get("lead_id") or lead.get("lead_id") or run_file.stem)
        pipeline_status = str(run.get("status") or "")
        status = status_overrides.get(lead_id, pipeline_status or "pendiente")

        tier = normalize_tier(run.get("tier") or (run.get("paco") or {}).get("tier"), pipeline_status)

        leads.append(
            {
                "lead_id": lead_id,
                "lead_name": run.get("lead_name") or lead.get("lead_name") or "Lead desconocido",
                "tier": tier,
                "manolo_model": str(run.get("manolo_model") or "").lower(),
                "status": status,
                "pipeline_status": pipeline_status,
                "sector": lead.get("sector") or "",
                "phone": lead.get("phone") or "",
                "address": lead.get("address") or lead.get("location", {}).get("address") or "",
                "municipality": lead.get("municipality") or lead.get("location", {}).get("municipality") or "",
                "plant_name": lead.get("plant_name") or "",
                "plant_surplus_pct": to_float(lead.get("plant_surplus_pct")),
                "distance_km": to_float(lead.get("distance_km")),
                "started_at": run.get("started_at"),
                "mensajes": extract_messages(run.get("manolo")),
            }
        )

    leads.sort(key=lambda x: (x.get("started_at") or ""), reverse=True)
    return leads


def load_plants() -> list[dict[str, Any]]:
    raw = parse_json_file(PLANTS_FILE)
    plants_raw = raw.get("solar_plants", []) if isinstance(raw, dict) else []
    plants: list[dict[str, Any]] = []
    for idx, p in enumerate(plants_raw, start=1):
        if not isinstance(p, dict):
            continue
        coords = p.get("coordinates") or {}
        name = str(p.get("name") or "")
        plant_id = str(p.get("id") or f"{name.lower().replace(' ', '_')}_{idx}")
        plants.append(
            {
                "id": plant_id,
                "name": name,
                "latitude": to_float(coords.get("latitude")),
                "longitude": to_float(coords.get("longitude")),
                "surplus": to_float(p.get("surplus_percentage")),
                "power_kw": to_float(p.get("power_kw")),
            }
        )
    return plants


def read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not csv_path.exists():
        return rows

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            rows.append(
                {
                    "lead_id": row.get("place_id") or f"custom_{idx}",
                    "lead_name": row.get("lead_name") or "Lead desconocido",
                    "tier": "C",
                    "manolo_model": "",
                    "status": "pendiente",
                    "pipeline_status": "custom_search",
                    "sector": row.get("sector") or "",
                    "phone": row.get("phone") or "",
                    "address": row.get("address") or "",
                    "municipality": row.get("municipality") or "",
                    "plant_name": row.get("plant_name") or "",
                    "plant_surplus_pct": to_float(row.get("plant_surplus_pct")),
                    "distance_km": to_float(row.get("distance_km")),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "mensajes": [],
                    "is_custom_search": True,
                    "place_id": row.get("place_id") or "",
                }
            )
    return rows


def run_custom_scraper(lat: float, lng: float, radius_km: float, plant_id: str | None) -> tuple[str, int, list[dict[str, Any]]]:
    cmd = [
        sys.executable,
        str(SCRAPER_CUSTOM_ZONE),
        "--lat",
        str(lat),
        "--lng",
        str(lng),
        "--radius-km",
        str(radius_km),
    ]
    if plant_id:
        cmd.extend(["--plant-id", plant_id])

    completed = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )

    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    csv_path = ""
    for line in output.splitlines():
        if line.startswith("OUTPUT_CSV="):
            csv_path = line.split("=", 1)[1].strip()
            break

    if completed.returncode != 0 or not csv_path:
        raise HTTPException(status_code=500, detail=f"Error ejecutando scraper_custom_zone.py:\n{output.strip()}")

    csv_file = Path(csv_path)
    leads = read_csv_rows(csv_file)
    return csv_path, len(leads), leads


def run_ingest(csv_path: str) -> tuple[str, int]:
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise HTTPException(status_code=404, detail=f"No existe CSV: {csv_path}")

    cmd = ["python3", str(INGEST_SCRIPT), str(csv_file)]
    completed = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")

    if completed.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error ejecutando ingest.py:\n{output.strip()}")

    # ingest.py imprime: ✅ {n} lead(s) guardados en {path}
    match = re.search(r"✅\s*(\d+)\s*lead\(s\)\s*guardados en\s*(.+)", output)
    if not match:
        raise HTTPException(status_code=500, detail=f"No se pudo parsear salida de ingest.py:\n{output.strip()}")

    lead_count = int(match.group(1))
    json_path = match.group(2).strip()
    return json_path, lead_count


def load_custom_search_history() -> list[dict[str, Any]]:
    data = parse_json_file(CUSTOM_SEARCH_HISTORY_FILE)
    if isinstance(data, list):
        return data
    return []


def save_custom_search_history(history: list[dict[str, Any]]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with CUSTOM_SEARCH_HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def append_custom_search(item: dict[str, Any]) -> None:
    history = load_custom_search_history()
    history.insert(0, item)
    save_custom_search_history(history[:200])


def mark_custom_search_ingested(csv_path: str, json_path: str) -> None:
    history = load_custom_search_history()
    changed = False
    for item in history:
        if str(item.get("csv_path", "")) == csv_path:
            item["ingested_at"] = datetime.now(timezone.utc).isoformat()
            item["json_path"] = json_path
            changed = True
            break
    if changed:
        save_custom_search_history(history)


def centroid_from_polygon(points: list[list[float]]) -> tuple[float, float]:
    if len(points) < 3:
        raise HTTPException(status_code=400, detail="polygon debe tener al menos 3 puntos")

    lat_sum = 0.0
    lng_sum = 0.0
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise HTTPException(status_code=400, detail="Cada punto del polygon debe ser [lat, lng]")
        lat_sum += float(point[0])
        lng_sum += float(point[1])

    count = float(len(points))
    return lat_sum / count, lng_sum / count


@app.get("/api/leads")
def get_leads() -> list[dict[str, Any]]:
    return load_leads()


@app.get("/api/stats")
def get_stats() -> dict[str, Any]:
    leads = load_leads()

    tier_a = sum(1 for l in leads if l.get("tier") == "A")
    tier_b = sum(1 for l in leads if l.get("tier") == "B")
    tier_c = sum(1 for l in leads if l.get("tier") == "C")
    discarded = sum(1 for l in leads if l.get("tier") == "DISCARD")
    aprobados = sum(1 for l in leads if str(l.get("pipeline_status")) == "aprobado")
    requiere_revision = sum(1 for l in leads if str(l.get("pipeline_status")) == "requiere_revisión")

    leads_por_planta: dict[str, int] = {}
    for lead in leads:
        plant = str(lead.get("plant_name") or "Sin planta")
        leads_por_planta[plant] = leads_por_planta.get(plant, 0) + 1

    return {
        "total_leads": len(leads),
        "tier_a": tier_a,
        "tier_b": tier_b,
        "tier_c": tier_c,
        "discarded": discarded,
        "aprobados": aprobados,
        "requiere_revision": requiere_revision,
        "leads_por_planta": leads_por_planta,
    }


@app.get("/api/plants")
def get_plants() -> list[dict[str, Any]]:
    return load_plants()


@app.get("/api/custom_searches")
def get_custom_searches() -> list[dict[str, Any]]:
    return load_custom_search_history()


@app.post("/api/search_custom_zone")
def search_custom_zone(payload: CustomZoneSearchPayload) -> dict[str, Any]:
    if payload.radius_km <= 0:
        raise HTTPException(status_code=400, detail="radius_km debe ser > 0")

    csv_path, lead_count, leads = run_custom_scraper(
        lat=payload.lat,
        lng=payload.lng,
        radius_km=payload.radius_km,
        plant_id=payload.plant_id,
    )

    append_custom_search(
        {
            "type": payload.zone_type or "circle",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "zone": {"lat": payload.lat, "lng": payload.lng, "radius_km": payload.radius_km},
            "plant_id": payload.plant_id,
            "csv_path": csv_path,
            "lead_count": lead_count,
        }
    )

    return {"csv_path": csv_path, "lead_count": lead_count, "leads": leads[:10]}


@app.post("/api/ingest_custom")
def ingest_custom(payload: IngestCustomPayload) -> dict[str, Any]:
    json_path, lead_count = run_ingest(payload.csv_path)
    mark_custom_search_ingested(payload.csv_path, json_path)
    return {"json_path": json_path, "lead_count": lead_count}


@app.post("/api/leads/{lead_id}/status")
def update_lead_status(lead_id: str, payload: StatusUpdate) -> dict[str, str]:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="status inválido")

    statuses = load_status_overrides()
    statuses[lead_id] = payload.status
    save_status_overrides(statuses)
    return {"lead_id": lead_id, "status": payload.status}


@app.get("/")
def dashboard_index() -> FileResponse:
    index = DASHBOARD_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="dashboard/index.html no encontrado")
    return FileResponse(index)


app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")
