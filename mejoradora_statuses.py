#!/usr/bin/env python3
"""Mapeo canonico de estados legacy a estados oficiales."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mejoradora_runtime import load_runtime_dict, load_runtime_list


OFFICIAL_REVIEW_STATUSES = {"pending", "approved", "needs_review", "rejected"}
OFFICIAL_CONTACT_STATUSES = {
    "not_queued",
    "queued",
    "ready",
    "contacted",
    "waiting_reply",
    "responded",
    "do_not_contact",
}
OFFICIAL_COMMERCIAL_STATUSES = {
    "no_opportunity",
    "opportunity_open",
    "qualified_opportunity",
    "proposal_sent",
    "negotiation",
    "won",
    "lost",
}


def normalize_tier(run: dict[str, Any]) -> str:
    lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
    tier = str(run.get("tier") or (run.get("paco") or {}).get("tier") or lead.get("tier") or "").upper().strip()
    return tier if tier in {"A", "B", "C", "DISCARD"} else "C"


def map_review_status(run: dict[str, Any]) -> str:
    """
    Mapeos ambiguos:
    - `tier_c_en_espera` -> `pending`
      Razon: expresa espera operativa, no aprobacion ni rechazo.
    - ausencia de estado -> `pending`
    """

    raw_status = str(run.get("status") or "").strip().lower()
    tier = normalize_tier(run)

    if raw_status == "aprobado":
        return "approved"
    if raw_status in {"requiere_revisión", "requiere_revision"}:
        return "needs_review"
    if raw_status == "descartado_por_paco" or tier == "DISCARD":
        return "rejected"
    if raw_status == "tier_c_en_espera":
        return "pending"
    return "pending"


def load_legacy_contact_status_map(runs_dir: Path) -> dict[str, str]:
    raw = load_runtime_dict(runs_dir / "lead_status.json")
    return {str(k): str(v) for k, v in raw.items()}


def load_legacy_whatsapp_sent_index(runs_dir: Path) -> tuple[set[str], set[str]]:
    entries = load_runtime_list(runs_dir / "whatsapp_sent.json")
    lead_ids: set[str] = set()
    place_ids: set[str] = set()

    for item in entries:
        if not isinstance(item, dict):
            continue
        lead_id = str(item.get("lead_id") or "").strip()
        place_id = str(item.get("place_id") or "").strip()
        if lead_id:
            lead_ids.add(lead_id)
        if place_id:
            place_ids.add(place_id)

    return lead_ids, place_ids


def map_contact_status(
    run: dict[str, Any],
    legacy_contact_statuses: dict[str, str] | None = None,
    whatsapp_sent_lead_ids: set[str] | None = None,
    whatsapp_sent_place_ids: set[str] | None = None,
) -> str:
    """
    Mapeos ambiguos:
    - `pendiente` -> `queued`
      Razon: hay intencion operativa de trabajar el lead, pero no evidencia de contacto.
    - `cerrado` -> `responded`
      Razon: el estado legacy no separa contacto y venta; se trata como ciclo
      de contacto cerrado, no como venta ganada.
    - envio en `whatsapp_sent.json` sin override manual -> `contacted`
    """

    lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
    lead_id = str(run.get("lead_id") or lead.get("lead_id") or "").strip()
    place_id = str(lead.get("place_id") or run.get("place_id") or "").strip()

    legacy_value = ""
    if legacy_contact_statuses and lead_id:
        legacy_value = str(legacy_contact_statuses.get(lead_id) or "").strip().lower()

    if legacy_value == "pendiente":
        return "queued"
    if legacy_value == "contactado":
        return "contacted"
    if legacy_value == "cerrado":
        return "responded"
    if legacy_value == "no_interesa":
        return "do_not_contact"

    if (whatsapp_sent_lead_ids and lead_id in whatsapp_sent_lead_ids) or (
        whatsapp_sent_place_ids and place_id and place_id in whatsapp_sent_place_ids
    ):
        return "contacted"

    return "not_queued"


def map_commercial_status(
    run: dict[str, Any],
    contact_status: str | None = None,
    legacy_contact_statuses: dict[str, str] | None = None,
) -> str:
    """
    No existe hoy una fuente legacy fiable de estado comercial.

    Decision:
    - `no_interesa` -> `lost`
    - todo lo demas -> `no_opportunity`
    """

    lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
    lead_id = str(run.get("lead_id") or lead.get("lead_id") or "").strip()
    legacy_value = ""
    if legacy_contact_statuses and lead_id:
        legacy_value = str(legacy_contact_statuses.get(lead_id) or "").strip().lower()

    if legacy_value == "no_interesa":
        return "lost"
    return "no_opportunity"


# DOBLE PRODUCTO SOLDELIA
OFFICIAL_SOLDELIA_STATUSES = {
    "not_contacted",
    "contacted",
    "factura_recibida",
    "estudio_enviado",
    "signed",
    "lost",
}

OFFICIAL_COMERCIALIZADORA_STATUSES = {
    "not_contacted",
    "contacted",
    "comparativa_enviada",
    "signed",
    "lost",
}


def default_soldelia_status() -> str:
    return "not_contacted"


def default_comercializadora_status() -> str:
    return "not_contacted"
