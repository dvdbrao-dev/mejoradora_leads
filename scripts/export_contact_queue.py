#!/usr/bin/env python3
"""Exportador formal de ContactQueue."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_contact_queue import ContactQueueItem, build_contact_queue_from_runs
from mejoradora_paths import get_project_paths
from mejoradora_plants import load_active_plant_ids


PATHS = get_project_paths(Path(__file__))
EXPORT_DIR = PATHS.outputs / "contact_queue"
STATE_PATH = PATHS.runtime / "contact_queue_state.json"


PRESET_FILTERS: dict[str, dict[str, Any]] = {
    "ready_for_review": {
        "review_status": {"pending", "needs_review"},
        "contact_status": {"not_queued", "queued", "ready"},
    },
    "ready_for_contact": {
        "review_status": {"approved"},
        "contact_status": {"not_queued", "queued", "ready"},
        "with_phone": True,
    },
    "contacted_pending_followup": {
        "contact_status": {"contacted", "waiting_reply"},
    },
    "do_not_contact": {
        "contact_status": {"do_not_contact"},
    },
}


def parse_csv_list(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {item.strip() for item in raw.split(",") if item.strip()}
    return values or None


def _merge_filters(args: argparse.Namespace) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "tier": parse_csv_list(args.tier),
        "review_status": parse_csv_list(args.review_status),
        "contact_status": parse_csv_list(args.contact_status),
        "commercial_status": parse_csv_list(args.commercial_status),
        "plant_id": args.plant_id,
        "with_phone": args.with_phone,
    }
    if not args.preset:
        return filters

    preset = PRESET_FILTERS[args.preset]
    for key in ("tier", "review_status", "contact_status", "commercial_status"):
        values = preset.get(key)
        if values:
            filters[key] = set(values) if filters.get(key) is None else set(filters[key]) & set(values)
    if preset.get("plant_id") and not filters["plant_id"]:
        filters["plant_id"] = preset["plant_id"]
    if preset.get("with_phone"):
        filters["with_phone"] = True
    return filters


def matches_filters(
    item: ContactQueueItem,
    filters: dict[str, Any],
    active_plant_ids: set[str] | None,
) -> bool:
    if active_plant_ids is not None and str(item.plant_id or "") not in active_plant_ids:
        return False

    tiers = filters["tier"]
    if tiers and item.tier not in tiers:
        return False

    review_statuses = filters["review_status"]
    if review_statuses and item.review_status not in review_statuses:
        return False

    contact_statuses = filters["contact_status"]
    if contact_statuses and item.contact_status not in contact_statuses:
        return False

    commercial_statuses = filters["commercial_status"]
    if commercial_statuses and item.commercial_status not in commercial_statuses:
        return False

    if filters["plant_id"] and str(item.plant_id or "") != filters["plant_id"]:
        return False

    if filters["with_phone"] and not item.phone:
        return False

    return True


def serialize_items(items: list[ContactQueueItem]) -> list[dict[str, Any]]:
    return [item.to_dict() for item in items]


def export_json(items: list[ContactQueueItem], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_items(items)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_csv(items: list[ContactQueueItem], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = serialize_items(items)
    fieldnames = [
        "queue_id",
        "lead_id",
        "plant_id",
        "business_name",
        "category",
        "distance_km",
        "estimated_consumption_band",
        "tier",
        "review_status",
        "contact_status",
        "commercial_status",
        "phone",
        "website",
        "suggested_channel",
        "message_preview",
        "reason_fit",
        "owner",
        "last_contact_at",
        "next_action",
        "notes",
        "created_at",
        "updated_at",
        "run_ref",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_output_base_name(args: argparse.Namespace) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return args.output_name or f"contact_queue_{timestamp}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta ContactQueue desde runs válidos")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--output-name", help="Nombre base del archivo de salida, sin extensión")
    parser.add_argument("--tier", help="Filtrar por tiers, ej. A,B")
    parser.add_argument("--review-status", help="Filtrar por review_status, ej. approved,needs_review")
    parser.add_argument("--contact-status", help="Filtrar por contact_status, ej. not_queued,contacted")
    parser.add_argument("--commercial-status", help="Filtrar por commercial_status, ej. no_opportunity,lost")
    parser.add_argument("--plant-id", help="Filtrar por plant_id exacto")
    parser.add_argument("--with-phone", action="store_true", help="Solo incluir leads con teléfono")
    parser.add_argument("--preset", choices=sorted(PRESET_FILTERS), help="Aplicar preset operativo documentado")
    parser.add_argument("--limit", type=int, help="Límite de resultados")
    parser.add_argument("--owner", help="Owner a asignar en la salida")
    parser.add_argument(
        "--include-non-active-plants",
        action="store_true",
        help="Incluir leads de plantas que no estén active en el catálogo oficial",
    )
    args = parser.parse_args()

    items = build_contact_queue_from_runs(PATHS.runs, owner=args.owner, operational_state_path=STATE_PATH)
    active_plant_ids = None if args.include_non_active_plants else load_active_plant_ids(PATHS.data / "plants.json")
    filters = _merge_filters(args)
    filtered = [item for item in items if matches_filters(item, filters, active_plant_ids)]

    if args.limit is not None and args.limit >= 0:
        filtered = filtered[: args.limit]

    base_name = build_output_base_name(args)
    json_path = EXPORT_DIR / f"{base_name}.json"
    csv_path = EXPORT_DIR / f"{base_name}.csv"

    if args.format in {"json", "both"}:
        export_json(filtered, json_path)
    if args.format in {"csv", "both"}:
        export_csv(filtered, csv_path)

    print(f"Exportados {len(filtered)} lead(s)")
    if filtered:
        sample = filtered[0]
        print(
            "Ejemplo:",
            json.dumps(
                {
                    "queue_id": sample.queue_id,
                    "business_name": sample.business_name,
                    "tier": sample.tier,
                    "review_status": sample.review_status,
                    "contact_status": sample.contact_status,
                    "commercial_status": sample.commercial_status,
                    "owner": sample.owner,
                    "next_action": sample.next_action,
                    "phone": sample.phone,
                },
                ensure_ascii=False,
            ),
        )
    if args.preset:
        print(f"Preset: {args.preset}")
    if args.format in {"json", "both"}:
        print(f"JSON: {json_path}")
    if args.format in {"csv", "both"}:
        print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
