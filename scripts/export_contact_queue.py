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


def parse_csv_list(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {item.strip() for item in raw.split(",") if item.strip()}
    return values or None


def matches_filters(item: ContactQueueItem, args: argparse.Namespace, active_plant_ids: set[str] | None) -> bool:
    if active_plant_ids is not None and str(item.plant_id or "") not in active_plant_ids:
        return False

    tiers = parse_csv_list(args.tier)
    if tiers and item.tier not in tiers:
        return False

    review_statuses = parse_csv_list(args.review_status)
    if review_statuses and item.review_status not in review_statuses:
        return False

    contact_statuses = parse_csv_list(args.contact_status)
    if contact_statuses and item.contact_status not in contact_statuses:
        return False

    commercial_statuses = parse_csv_list(args.commercial_status)
    if commercial_statuses and item.commercial_status not in commercial_statuses:
        return False

    if args.plant_id and str(item.plant_id or "") != args.plant_id:
        return False

    if args.with_phone and not item.phone:
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
        "created_at",
        "updated_at",
        "run_ref",
        "soldelia_status",
        "comercializadora_status",
        "kwh_adjudicados",
        "comision_soldelia_ano1_eur",
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
    parser.add_argument("--limit", type=int, help="Límite de resultados")
    parser.add_argument("--owner", help="Owner a asignar en la salida")
    parser.add_argument(
        "--include-non-active-plants",
        action="store_true",
        help="Incluir leads de plantas que no estén active en el catálogo oficial",
    )
    args = parser.parse_args()

    items = build_contact_queue_from_runs(PATHS.runs, owner=args.owner)
    active_plant_ids = None if args.include_non_active_plants else load_active_plant_ids(PATHS.data / "plants.json")
    filtered = [item for item in items if matches_filters(item, args, active_plant_ids)]

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
                    "phone": sample.phone,
                },
                ensure_ascii=False,
            ),
        )
    if args.format in {"json", "both"}:
        print(f"JSON: {json_path}")
    if args.format in {"csv", "both"}:
        print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
