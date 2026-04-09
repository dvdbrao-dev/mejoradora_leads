#!/usr/bin/env python3
"""Exporta mensajes de Manolo desde runs a un CSV."""

import csv
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_paths import get_project_paths
from mejoradora_runtime import iter_valid_run_records


PATHS = get_project_paths(Path(__file__))
RUNS_DIR = PATHS.runs
OUTPUTS_DIR = BASE_DIR / "outputs"


def load_runs() -> list[dict]:
    return [run for _, run in iter_valid_run_records(RUNS_DIR)]


def get_lead_field(lead: dict, key: str, default: str = "") -> str:
    if key in lead and lead.get(key) not in (None, ""):
        return str(lead.get(key))

    if key == "address":
        return str(lead.get("location", {}).get("address", default))
    if key == "phone":
        return str(lead.get("contact", {}).get("phone", default))
    return str(default)


def normalize_manolo_output(manolo: object) -> list[dict]:
    if isinstance(manolo, list):
        return [m for m in manolo if isinstance(m, dict)]
    if isinstance(manolo, dict):
        return [manolo]
    return []


def export_messages() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    headers = [
        "lead_name",
        "tier",
        "sector",
        "address",
        "phone",
        "plant_name",
        "distance_km",
        "plant_surplus_pct",
        "variante",
        "mensaje",
        "cta",
        "confidence_level",
    ]

    rows = []
    exported_leads = 0

    for run in load_runs():
        status = run.get("status", "")
        if status == "descartado_por_paco":
            continue

        manolo_variants = normalize_manolo_output(run.get("manolo"))
        if not manolo_variants:
            continue

        exported_leads += 1
        lead = run.get("lead", {}) if isinstance(run.get("lead"), dict) else {}
        lead_name = run.get("lead_name") or lead.get("lead_name", "")
        tier = run.get("tier") or run.get("paco", {}).get("tier", "")
        sector = get_lead_field(lead, "sector", "")
        address = get_lead_field(lead, "address", "")
        phone = get_lead_field(lead, "phone", "")
        plant_name = get_lead_field(lead, "plant_name", "")
        distance_km = get_lead_field(lead, "distance_km", "")
        plant_surplus_pct = get_lead_field(lead, "plant_surplus_pct", "")

        for variant in manolo_variants:
            rows.append(
                {
                    "lead_name": lead_name,
                    "tier": tier,
                    "sector": sector,
                    "address": address,
                    "phone": phone,
                    "plant_name": plant_name,
                    "distance_km": distance_km,
                    "plant_surplus_pct": plant_surplus_pct,
                    "variante": variant.get("variant", ""),
                    "mensaje": variant.get("message", ""),
                    "cta": variant.get("cta", ""),
                    "confidence_level": variant.get("confidence_level", ""),
                }
            )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUTS_DIR / f"mensajes_{timestamp}.csv"

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{exported_leads} leads exportados, {len(rows)} mensajes totales")
    print(f"CSV generado en: {out_path}")


if __name__ == "__main__":
    export_messages()
