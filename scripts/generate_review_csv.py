#!/usr/bin/env python3
"""Genera CSV de revisión manual para leads Tier A+B."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = BASE_DIR / "runs"
OUTPUT_PATH = BASE_DIR / "data" / "comercial" / "leads_revision.csv"

SKIP_RUN_FILES = {
    "enriched.json",
    "lead_status.json",
    "whatsapp_sent.json",
    "custom_searches.json",
}

FIELDNAMES = [
    "lead_id",
    "lead_name",
    "tier",
    "sector",
    "notes",
    "municipality",
    "province",
    "phone",
    "distance_km",
    "plant_name",
    "paco_why",
    "manolo_autoridad",
    "viable",
    "motivo_rechazo",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def load_run(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def get_phone(lead: dict[str, Any]) -> str:
    contact = lead.get("contact") if isinstance(lead.get("contact"), dict) else {}
    return clean_text(lead.get("phone") or contact.get("phone"))


def get_location_field(lead: dict[str, Any], field: str) -> str:
    location = lead.get("location") if isinstance(lead.get("location"), dict) else {}
    return clean_text(lead.get(field) or location.get(field))


def get_manolo_autoridad(run: dict[str, Any]) -> str:
    manolo = run.get("manolo")
    if isinstance(manolo, dict):
        variants = [manolo]
    elif isinstance(manolo, list):
        variants = [item for item in manolo if isinstance(item, dict)]
    else:
        variants = []

    for variant in variants:
        variant_type = clean_text(variant.get("tipo") or variant.get("type")).casefold()
        if variant_type != "autoridad":
            continue
        message = clean_text(variant.get("mensaje") or variant.get("message"))
        return message[:160]
    return ""


def run_to_row(run: dict[str, Any]) -> dict[str, str]:
    lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
    paco = run.get("paco") if isinstance(run.get("paco"), dict) else {}

    return {
        "lead_id": clean_text(run.get("lead_id") or lead.get("lead_id")),
        "lead_name": clean_text(run.get("lead_name") or lead.get("lead_name")),
        "tier": clean_text(run.get("tier") or paco.get("tier")),
        "sector": clean_text(lead.get("sector")),
        "notes": clean_text(lead.get("notes")),
        "municipality": get_location_field(lead, "municipality"),
        "province": get_location_field(lead, "province"),
        "phone": get_phone(lead),
        "distance_km": clean_text(lead.get("distance_km")),
        "plant_name": clean_text(lead.get("plant_name")),
        "paco_why": clean_text(paco.get("why")),
        "manolo_autoridad": get_manolo_autoridad(run),
        "viable": "",
        "motivo_rechazo": "",
    }


def tier_sort_key(row: dict[str, str]) -> tuple[int, str]:
    tier_rank = {"A": 0, "B": 1}.get(row["tier"], 9)
    return tier_rank, row["lead_name"].casefold()


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        if path.name in SKIP_RUN_FILES or any(token in path.name for token in ("enriched", "status", "whatsapp", "custom")):
            continue
        run = load_run(path)
        if run is None:
            continue

        row = run_to_row(run)
        if row["tier"] in {"A", "B"}:
            rows.append(row)

    rows.sort(key=tier_sort_key)
    return rows


def main() -> None:
    rows = build_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV generado: {OUTPUT_PATH}")
    print(f"Leads exportados: {len(rows)}")


if __name__ == "__main__":
    main()
