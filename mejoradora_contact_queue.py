#!/usr/bin/env python3
"""Contrato inicial y helpers de ContactQueue."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mejoradora_runtime import iter_valid_run_records
from mejoradora_statuses import (
    default_comercializadora_status,
    default_soldelia_status,
    load_legacy_contact_status_map,
    load_legacy_whatsapp_sent_index,
    map_commercial_status,
    map_contact_status,
    map_review_status,
    normalize_tier,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_message_preview(run: dict[str, Any]) -> str | None:
    manolo = run.get("manolo")
    variants: list[dict[str, Any]] = []

    if isinstance(manolo, list):
        variants = [item for item in manolo if isinstance(item, dict)]
    elif isinstance(manolo, dict):
        variants = [manolo]

    for variant in variants:
        message = str(variant.get("message") or "").strip()
        if message:
            return message[:280]
    return None


def _extract_reason_fit(run: dict[str, Any]) -> str | None:
    for candidate in (
        (run.get("paco") or {}).get("why"),
        (run.get("esther") or {}).get("exec_summary"),
        (run.get("auditor") or {}).get("reason"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _infer_channel(phone: str | None, website: str | None) -> str:
    if phone:
        return "whatsapp"
    if website:
        return "web"
    return "manual"


@dataclass
class ContactQueueItem:
    """
    Campos obligatorios:
    - queue_id
    - lead_id
    - business_name
    - tier
    - review_status
    - contact_status
    - commercial_status
    - created_at
    - updated_at

    Campos opcionales:
    - plant_id
    - category
    - distance_km
    - estimated_consumption_band
    - phone
    - website
    - suggested_channel
    - message_preview
    - reason_fit
    - owner
    """

    queue_id: str
    lead_id: str
    business_name: str
    tier: str
    review_status: str
    contact_status: str
    commercial_status: str
    created_at: str
    updated_at: str
    plant_id: str | None = None
    category: str | None = None
    distance_km: float | None = None
    estimated_consumption_band: str | None = None
    phone: str | None = None
    website: str | None = None
    suggested_channel: str | None = None
    message_preview: str | None = None
    reason_fit: str | None = None
    owner: str | None = None
    run_ref: str | None = None
    soldelia_status: str = default_soldelia_status()
    comercializadora_status: str = default_comercializadora_status()
    kwh_adjudicados: float | None = None
    comision_soldelia_ano1_eur: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_contact_queue_item(
    run: dict[str, Any],
    source_path: Path | None = None,
    owner: str | None = None,
    legacy_contact_statuses: dict[str, str] | None = None,
    whatsapp_sent_lead_ids: set[str] | None = None,
    whatsapp_sent_place_ids: set[str] | None = None,
) -> ContactQueueItem | None:
    lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
    lead_id = str(run.get("lead_id") or lead.get("lead_id") or "").strip()
    business_name = str(run.get("lead_name") or lead.get("lead_name") or "").strip()

    if not lead_id or not business_name:
        return None

    phone = str(lead.get("phone") or (lead.get("contact") or {}).get("phone") or "").strip() or None
    website = str(lead.get("website") or "").strip() or None
    created_at = str(run.get("started_at") or run.get("created_at") or _utc_now_iso())
    updated_at = str(run.get("finished_at") or run.get("updated_at") or created_at)
    review_status = map_review_status(run)
    contact_status = map_contact_status(
        run,
        legacy_contact_statuses=legacy_contact_statuses,
        whatsapp_sent_lead_ids=whatsapp_sent_lead_ids,
        whatsapp_sent_place_ids=whatsapp_sent_place_ids,
    )
    commercial_status = map_commercial_status(
        run,
        contact_status=contact_status,
        legacy_contact_statuses=legacy_contact_statuses,
    )

    plant_id = str(lead.get("plant_id") or "").strip() or None
    item = ContactQueueItem(
        queue_id=f"cq_{lead_id}",
        lead_id=lead_id,
        plant_id=plant_id,
        business_name=business_name,
        category=str(lead.get("sector") or "").strip() or None,
        distance_km=_to_float(lead.get("distance_km")),
        estimated_consumption_band=str(
            (run.get("paco") or {}).get("estimated_consumption_band")
            or lead.get("estimated_consumption_band")
            or lead.get("energy_signal")
            or ""
        ).strip()
        or None,
        tier=normalize_tier(run),
        review_status=review_status,
        contact_status=contact_status,
        commercial_status=commercial_status,
        phone=phone,
        website=website,
        suggested_channel=_infer_channel(phone, website),
        message_preview=_extract_message_preview(run),
        reason_fit=_extract_reason_fit(run),
        owner=str(owner or "").strip() or None,
        created_at=created_at,
        updated_at=updated_at,
        run_ref=source_path.name if source_path is not None else None,
    )

    if source_path is not None and not item.reason_fit:
        item.reason_fit = f"Origen: {source_path.name}"
    return item


def build_contact_queue_from_runs(runs_dir: Path, owner: str | None = None) -> list[ContactQueueItem]:
    items: list[ContactQueueItem] = []
    legacy_contact_statuses = load_legacy_contact_status_map(runs_dir)
    whatsapp_sent_lead_ids, whatsapp_sent_place_ids = load_legacy_whatsapp_sent_index(runs_dir)

    for path, run in iter_valid_run_records(runs_dir):
        item = build_contact_queue_item(
            run=run,
            source_path=path,
            owner=owner,
            legacy_contact_statuses=legacy_contact_statuses,
            whatsapp_sent_lead_ids=whatsapp_sent_lead_ids,
            whatsapp_sent_place_ids=whatsapp_sent_place_ids,
        )
        if item is not None:
            items.append(item)
    return items
