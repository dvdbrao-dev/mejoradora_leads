#!/usr/bin/env python3
"""
ingest.py — Agente Intake de Openfang
Lee leads desde CSV, JSON o entrada manual y los normaliza al schema estándar.
"""

import json
import csv
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "inputs" / "raw"
CLEAN_DIR = BASE_DIR / "inputs" / "cleaned"

SECTOR_MAP = {
    "bar": "hostelería",
    "restaurante": "hostelería",
    "cafetería": "hostelería",
    "taller": "taller",
    "mecánico": "taller",
    "ayuntamiento": "ayuntamiento",
    "comercio": "comercio",
    "tienda": "comercio",
    "finca": "administración_fincas",
    "comunidad": "administración_fincas",
    "fábrica": "industria",
    "nave": "industria",
}

ENERGY_SIGNALS = {
    "hostelería": "alto consumo probable",
    "taller": "alto consumo probable",
    "industria": "alto consumo probable",
    "ayuntamiento": "consumo medio estimado",
    "comercio": "consumo medio estimado",
    "administración_fincas": "consumo medio estimado",
    "particular": "bajo consumo",
    "otro": "desconocido",
}


def normalize_sector(raw_sector: str) -> str:
    raw = raw_sector.lower().strip()
    for key, value in SECTOR_MAP.items():
        if key in raw:
            return value
    return "otro"


def generate_lead_id(name: str) -> str:
    slug = name.lower().replace(" ", "_")[:20]
    short_uuid = str(uuid.uuid4())[:8]
    return f"{slug}_{short_uuid}"


def normalize_lead(raw: dict) -> dict:
    sector = normalize_sector(raw.get("sector", "otro"))
    now = datetime.now(timezone.utc).isoformat()

    lead = {
        "lead_id": raw.get("lead_id") or generate_lead_id(raw.get("lead_name", "lead")),
        "lead_name": raw.get("lead_name", "").strip(),
        "sector": sector,
        "location": {
            "municipality": raw.get("municipality", raw.get("location", "")),
            "province": raw.get("province", ""),
            "address": raw.get("address", ""),
        },
        "contact": {
            "phone": raw.get("phone", raw.get("telefono", "")),
            "email": raw.get("email", ""),
            "name": raw.get("contact_name", ""),
            "role": raw.get("contact_role", ""),
        },
        "source": raw.get("source", "manual"),
        "roof_possible": raw.get("roof_possible", sector in ["hostelería", "taller", "industria", "ayuntamiento"]),
        "energy_signal": raw.get("energy_signal", ENERGY_SIGNALS.get(sector, "desconocido")),
        "last_invoice_available": bool(raw.get("last_invoice_available", False)),
        "last_invoice_kwh": raw.get("last_invoice_kwh", None),
        "contact_status": raw.get("contact_status", "sin contactar"),
        "notes": raw.get("notes", ""),
        "created_at": raw.get("created_at", now),
        "updated_at": now,
    }

    # Remove None values for cleanliness
    lead = {k: v for k, v in lead.items() if v is not None}
    # Conservar campos extra (ej. plant_id, plant_name, etc.)
    extra_fields = {k: v for k, v in raw.items() 
                    if k not in lead and v}
    lead.update(extra_fields)
    return lead


def ingest_csv(filepath: Path) -> list[dict]:
    leads = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(normalize_lead(dict(row)))
    return leads


def ingest_json(filepath: Path) -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [normalize_lead(item) for item in data]
    return [normalize_lead(data)]


def save_clean(leads: list[dict], source_name: str):
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = CLEAN_DIR / f"{source_name}_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(leads)} lead(s) guardados en {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Openfang Intake Agent")
    parser.add_argument("input", help="Archivo de entrada (CSV o JSON)")
    parser.add_argument("--preview", action="store_true", help="Solo mostrar resultado, no guardar")
    args = parser.parse_args()

    filepath = Path(args.input)
    if not filepath.exists():
        print(f"❌ Archivo no encontrado: {filepath}")
        return

    if filepath.suffix == ".csv":
        leads = ingest_csv(filepath)
    elif filepath.suffix == ".json":
        leads = ingest_json(filepath)
    else:
        print("❌ Formato no soportado. Usa CSV o JSON.")
        return

    if args.preview:
        print(json.dumps(leads, ensure_ascii=False, indent=2))
    else:
        save_clean(leads, filepath.stem)


if __name__ == "__main__":
    main()
