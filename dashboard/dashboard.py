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
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from dashboard.routers import dashboard_v2
except ModuleNotFoundError:
    from routers import dashboard_v2

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_paths import get_project_paths
from mejoradora_plants import load_dashboard_plants
from mejoradora_runtime import iter_valid_run_records, load_json_file, load_runtime_dict, load_runtime_list


PATHS = get_project_paths(Path(__file__))
RUNS_DIR = PATHS.runs
PLANTS_FILE = PATHS.data / "plants.json"
STATUS_FILE = RUNS_DIR / "lead_status.json"
CUSTOM_SEARCH_HISTORY_FILE = RUNS_DIR / "custom_searches.json"
DASHBOARD_DIR = PATHS.dashboard
SCRAPER_CUSTOM_ZONE = BASE_DIR / "scripts" / "scraper_custom_zone.py"
INGEST_SCRIPT = BASE_DIR / "scripts" / "ingest.py"

app = FastAPI(title="Mejoradora Leads Dashboard", version="1.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(dashboard_v2.router)


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
    return load_json_file(path)


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
    return load_runtime_dict(STATUS_FILE)


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

    for run_file, run in iter_valid_run_records(RUNS_DIR):
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
                "plant_id": lead.get("plant_id") or "",
                "plant_name": lead.get("plant_name") or "",
                "plant_surplus_pct": to_float(lead.get("plant_surplus_pct")),
                "distance_km": to_float(lead.get("distance_km")),
                "started_at": run.get("started_at"),
                "mensajes": extract_messages(run.get("manolo")),
            }
        )

    leads.sort(key=lambda x: (x.get("started_at") or ""), reverse=True)
    return leads


def load_plants(status: str | None = "active") -> list[dict[str, Any]]:
    return load_dashboard_plants(PLANTS_FILE, status=status)


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
    data = load_runtime_list(CUSTOM_SEARCH_HISTORY_FILE)
    return [item for item in data if isinstance(item, dict)]


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


@app.get("/api/stats/soldelia")
def get_soldelia_stats() -> dict[str, Any]:
    leads = load_leads()
    plants = load_plants(status=None)

    tier_a = sum(1 for lead in leads if lead.get("tier") == "A")
    tier_b = sum(1 for lead in leads if lead.get("tier") == "B")
    tier_c = sum(1 for lead in leads if lead.get("tier") == "C")
    discard = sum(1 for lead in leads if lead.get("tier") == "DISCARD")
    with_phone = sum(1 for lead in leads if str(lead.get("phone") or "").strip())

    top_plants = sorted(
        (
            plant.get("name")
            for plant in plants
            if isinstance(plant, dict) and str(plant.get("name") or "").strip()
        )
    )[:5]

    return {
        "total_leads": len(leads),
        "tier_a": tier_a,
        "tier_b": tier_b,
        "tier_c": tier_c,
        "discard": discard,
        "con_telefono": with_phone,
        "plantas_activas": len(plants),
        "plantas_top": top_plants,
        "comision_estimada_ano1_eur": (tier_a + tier_b) * 50,
    }


@app.get("/api/plants")
def get_plants(status: str = "active") -> list[dict[str, Any]]:
    return load_plants(status=None if status == "all" else status)


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


@app.get("/api/export/teleop")
def export_teleop(
    plant_id: str | None = None,
    tier: str = "A,B",
) -> StreamingResponse:
    """Genera y descarga CSV optimizado para teleoperadora."""
    leads = load_leads()

    tiers = {t.strip().upper() for t in tier.split(",") if t.strip()}
    leads = [lead for lead in leads if lead.get("tier") in tiers]

    if plant_id:
        leads = [lead for lead in leads if lead.get("plant_id") == plant_id]

    leads = [lead for lead in leads if str(lead.get("phone") or "").strip()]

    leads.sort(
        key=lambda lead: (
            0 if lead.get("tier") == "A" else 1,
            float(lead.get("distance_km") or 999),
        )
    )

    paco_why_by_lead_id: dict[str, str] = {}
    skip_files = {"enriched.json", "lead_status.json", "whatsapp_sent.json", "custom_searches.json"}
    for fp in RUNS_DIR.glob("*.json"):
        if fp.name in skip_files:
            continue
        try:
            with fp.open("r", encoding="utf-8") as handle:
                run = json.load(handle)
        except Exception:
            continue

        lead_id = str(run.get("lead_id") or "")
        if not lead_id:
            continue
        paco_why_by_lead_id[lead_id] = str((run.get("paco") or {}).get("why") or "")

    import io

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "Negocio",
            "Sector",
            "Telefono",
            "Direccion",
            "Distancia_km",
            "Planta",
            "Tier",
            "Argumento",
        ],
    )
    writer.writeheader()
    for lead in leads:
        writer.writerow(
            {
                "Negocio": lead.get("lead_name", ""),
                "Sector": lead.get("sector", ""),
                "Telefono": lead.get("phone", ""),
                "Direccion": lead.get("address", ""),
                "Distancia_km": lead.get("distance_km", ""),
                "Planta": lead.get("plant_name", ""),
                "Tier": lead.get("tier", ""),
                "Argumento": paco_why_by_lead_id.get(str(lead.get("lead_id") or ""), ""),
            }
        )

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"teleop_{plant_id or 'todas'}_{timestamp}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")
