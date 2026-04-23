"""Endpoints v2 para el dashboard comercial."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from event_log import EventLog, FUNNEL_ORDER


router = APIRouter(prefix="/api/dashboard", tags=["dashboard_v2"])

RUNS_DIR = REPO_ROOT / "runs"
PLANTS_PATH = REPO_ROOT / "data" / "plants_soldelia.json"
EVENT_LOG = EventLog(REPO_ROOT / "data" / "logs" / "lead_events.jsonl")
COMMISSION_PER_KWH = 0.00639
RUN_SKIP_FILES = {"enriched.json", "lead_status.json", "whatsapp_sent.json", "custom_searches.json"}


class AdvanceRequest(BaseModel):
    event_type: str
    data: dict[str, Any] | None = None


class NoteRequest(BaseModel):
    text: str


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_runs() -> list[dict[str, Any]]:
    leads: list[dict[str, Any]] = []
    for fp in sorted(RUNS_DIR.glob("*.json")):
        if fp.name in RUN_SKIP_FILES:
            continue
        try:
            with fp.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue

        lead = data.get("lead") if isinstance(data.get("lead"), dict) else {}
        paco = data.get("paco") if isinstance(data.get("paco"), dict) else {}
        tier = str(data.get("tier") or paco.get("tier") or "").upper().strip() or "C"
        lead_id = str(data.get("lead_id") or lead.get("lead_id") or fp.stem)
        estimated_kwh = _to_float(paco.get("estimated_kwh_annual"))

        leads.append(
            {
                "lead_id": lead_id,
                "lead_name": data.get("lead_name") or lead.get("lead_name") or "Lead desconocido",
                "tier": tier,
                "sector": lead.get("sector") or "",
                "municipality": lead.get("municipality") or "",
                "province": lead.get("province") or "",
                "phone": lead.get("phone") or lead.get("contact", {}).get("phone") or "",
                "address": lead.get("address") or lead.get("location", {}).get("address") or "",
                "website": lead.get("website") or "",
                "lat": _to_float(lead.get("lat")),
                "lng": _to_float(lead.get("lng") or lead.get("lon")),
                "plant_id": lead.get("plant_id") or "",
                "plant_name": lead.get("plant_name") or "",
                "distance_km": _to_float(lead.get("distance_km")),
                "estimated_kwh_annual": estimated_kwh,
                "why": paco.get("why") or "",
                "started_at": data.get("started_at") or "",
            }
        )
    return leads


def _load_plants() -> list[dict[str, Any]]:
    with PLANTS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    plants = data.get("plants", data) if isinstance(data, dict) else data
    if isinstance(plants, dict):
        return list(plants.values())
    return [plant for plant in plants if isinstance(plant, dict)]


def _lead_name_map(leads: list[dict[str, Any]]) -> dict[str, str]:
    return {str(lead.get("lead_id") or ""): str(lead.get("lead_name") or "") for lead in leads}


@router.get("/overview")
def overview() -> dict[str, Any]:
    leads = _load_runs()
    plants = _load_plants()
    statuses = EVENT_LOG.all_lead_statuses()

    tier_counts = {"A": 0, "B": 0, "C": 0, "DISCARD": 0}
    for lead in leads:
        tier = str(lead.get("tier") or "DISCARD")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    sms_sent = sum(1 for status in statuses.values() if status == "sms_sent")
    sms_failed = sum(1 for status in statuses.values() if status == "sms_failed")
    responded = sum(
        1
        for status in statuses.values()
        if status in {"whatsapp_received", "call_done", "visit_done", "study_sent", "proposal_sent", "closed_won"}
    )
    visits_done = sum(1 for status in statuses.values() if status in {"visit_done", "study_sent", "proposal_sent", "closed_won"})
    closed_won = sum(1 for status in statuses.values() if status == "closed_won")
    closed_lost = sum(1 for status in statuses.values() if status == "closed_lost")

    total_kwh = sum((lead.get("estimated_kwh_annual") or 0.0) for lead in leads if lead.get("tier") in {"A", "B"})
    closed_kwh = sum(
        (lead.get("estimated_kwh_annual") or 0.0)
        for lead in leads
        if statuses.get(str(lead.get("lead_id") or "")) == "closed_won"
    )

    return {
        "leads": {
            "total": len(leads),
            "tier_a": tier_counts["A"],
            "tier_b": tier_counts["B"],
            "tier_c": tier_counts["C"],
            "discard": tier_counts["DISCARD"],
            "con_telefono": sum(1 for lead in leads if str(lead.get("phone") or "").strip()),
            "con_coordenadas": sum(1 for lead in leads if lead.get("lat") is not None and lead.get("lng") is not None),
        },
        "pipeline": {
            "sms_sent": sms_sent,
            "sms_failed": sms_failed,
            "responded": responded,
            "visits_done": visits_done,
            "closed_won": closed_won,
            "closed_lost": closed_lost,
        },
        "financiero": {
            "comision_potencial_eur": round(total_kwh * COMMISSION_PER_KWH, 2),
            "comision_cerrada_eur": round(closed_kwh * COMMISSION_PER_KWH, 2),
            "comision_proyectada_year1_eur": round(total_kwh * COMMISSION_PER_KWH * 0.15, 2),
            "plantas_activas": sum(1 for plant in plants if plant.get("status") == "active"),
        },
    }


@router.get("/pipeline")
def pipeline() -> dict[str, Any]:
    leads = _load_runs()
    statuses = EVENT_LOG.all_lead_statuses()

    counts = {stage: 0 for stage in FUNNEL_ORDER}
    counts["pending"] = max(len(leads) - len(statuses), 0)
    for status in statuses.values():
        if status in counts:
            counts[status] += 1

    total = len(leads)
    items = []
    for stage in FUNNEL_ORDER:
        if stage == "sms_failed":
            continue
        count = counts.get(stage, 0)
        items.append(
            {
                "stage": stage,
                "count": count,
                "percentage": round((100 * count / total), 1) if total else 0.0,
            }
        )
    return {"funnel": items, "total": total}


@router.get("/leads")
def leads_filtered(
    tier: str | None = None,
    sector: str | None = None,
    municipality: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    leads = _load_runs()
    statuses = EVENT_LOG.all_lead_statuses()

    for lead in leads:
        lead["contact_status"] = statuses.get(str(lead.get("lead_id") or ""), "pending")

    if tier:
        tiers = {part.strip().upper() for part in tier.split(",") if part.strip()}
        leads = [lead for lead in leads if str(lead.get("tier") or "").upper() in tiers]
    if sector:
        token = sector.lower()
        leads = [lead for lead in leads if token in str(lead.get("sector") or "").lower()]
    if municipality:
        token = municipality.lower()
        leads = [lead for lead in leads if token in str(lead.get("municipality") or "").lower()]
    if status:
        wanted = {part.strip() for part in status.split(",") if part.strip()}
        leads = [lead for lead in leads if str(lead.get("contact_status") or "") in wanted]

    leads.sort(
        key=lambda lead: (
            {"A": 0, "B": 1, "C": 2, "DISCARD": 3}.get(str(lead.get("tier") or ""), 9),
            str(lead.get("lead_name") or ""),
        )
    )
    total = len(leads)
    return {"total": total, "limit": limit, "offset": offset, "leads": leads[offset : offset + limit]}


@router.get("/timeline")
def timeline(days: int = 7, limit: int = 50) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    leads = _load_runs()
    names = _lead_name_map(leads)

    items: list[dict[str, Any]] = []
    for event in EVENT_LOG.all_events() or []:
        try:
            ts = datetime.fromisoformat(str(event.get("timestamp")))
        except Exception:
            continue
        if ts < cutoff:
            continue
        enriched = dict(event)
        data = dict(enriched.get("data") or {})
        if "lead_name" not in data:
            data["lead_name"] = names.get(str(event.get("lead_id") or ""), "")
        enriched["data"] = data
        items.append(enriched)

    items.sort(key=lambda event: str(event.get("timestamp") or ""), reverse=True)
    return {"events": items[:limit], "total": len(items)}


@router.get("/services")
def services() -> dict[str, Any]:
    result: dict[str, Any] = {
        "dashboard": {"status": "up", "port": 8001},
        "hermes": {"status": "unknown", "port": 3000},
        "cron": {"status": "unknown", "tasks": []},
        "sms": {"credit": None},
    }

    try:
        process = subprocess.run(["lsof", "-i", ":3000"], capture_output=True, text=True, timeout=3, check=False)
        result["hermes"]["status"] = "up" if process.returncode == 0 and process.stdout.strip() else "down"
    except Exception:
        pass

    try:
        process = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=3, check=False)
        if process.returncode == 0:
            tasks = [line for line in process.stdout.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            result["cron"]["status"] = "active" if tasks else "empty"
            result["cron"]["tasks"] = tasks[:5]
    except Exception:
        pass

    user = os.getenv("DINAHOSTING_USER")
    pwd = os.getenv("DINAHOSTING_PASS")
    account = os.getenv("DINAHOSTING_ACCOUNT")
    if user and pwd and account:
        try:
            response = requests.post(
                "https://dinahosting.com/special/api.php",
                data={
                    "AUTH_USER": user,
                    "AUTH_PWD": pwd,
                    "command": "Sms_GetCredit",
                    "account": account,
                    "responseType": "Json",
                },
                timeout=5,
            )
            payload = response.json()
            if payload.get("responseCode") == 1000:
                result["sms"]["credit"] = payload.get("data")
        except Exception:
            pass

    return result


@router.get("/map")
def map_data() -> dict[str, Any]:
    leads = _load_runs()
    plants = _load_plants()
    statuses = EVENT_LOG.all_lead_statuses()

    plant_markers = [
        {
            "type": "plant",
            "id": plant.get("plant_id"),
            "name": plant.get("name"),
            "lat": _to_float(plant.get("lat")),
            "lng": _to_float(plant.get("lon")),
            "power_kw": plant.get("power_kw"),
            "municipality": plant.get("municipality"),
            "status": plant.get("status"),
        }
        for plant in plants
        if _to_float(plant.get("lat")) is not None and _to_float(plant.get("lon")) is not None
    ]

    lead_markers = [
        {
            "type": "lead",
            "id": lead.get("lead_id"),
            "name": lead.get("lead_name"),
            "lat": lead.get("lat"),
            "lng": lead.get("lng"),
            "tier": lead.get("tier"),
            "sector": lead.get("sector"),
            "municipality": lead.get("municipality"),
            "contact_status": statuses.get(str(lead.get("lead_id") or ""), "pending"),
            "distance_km": lead.get("distance_km"),
            "plant_name": lead.get("plant_name"),
        }
        for lead in leads
        if lead.get("lat") is not None and lead.get("lng") is not None
    ]

    return {
        "plants": plant_markers,
        "leads": lead_markers,
        "center": {"lat": 37.1773, "lng": -3.5986},
    }


@router.post("/lead/{lead_id}/advance")
def advance_lead(lead_id: str, req: AdvanceRequest) -> dict[str, Any]:
    if req.event_type not in FUNNEL_ORDER:
        raise HTTPException(status_code=400, detail=f"event_type inválido. Usar: {FUNNEL_ORDER}")
    event = EVENT_LOG.record(lead_id=lead_id, event_type=req.event_type, data=req.data or {})
    return {"ok": True, "event": event}


@router.post("/lead/{lead_id}/note")
def add_note(lead_id: str, req: NoteRequest) -> dict[str, Any]:
    event = EVENT_LOG.record(lead_id=lead_id, event_type="note", data={"text": req.text})
    return {"ok": True, "event": event}
