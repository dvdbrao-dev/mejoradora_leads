#!/usr/bin/env python3
import json
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
DASHBOARD_DIR = BASE_DIR / "dashboard"

app = FastAPI(title="Openfang Dashboard", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatusUpdate(BaseModel):
    status: str


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
        if run_file.name == STATUS_FILE.name:
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
    for p in plants_raw:
        if not isinstance(p, dict):
            continue
        coords = p.get("coordinates") or {}
        plants.append(
            {
                "name": p.get("name", ""),
                "latitude": to_float(coords.get("latitude")),
                "longitude": to_float(coords.get("longitude")),
                "surplus": to_float(p.get("surplus_percentage")),
                "power_kw": to_float(p.get("power_kw")),
            }
        )
    return plants


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


# Permite servir archivos adicionales en dashboard/ si se agregan en el futuro.
app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")
