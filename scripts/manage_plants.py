#!/usr/bin/env python3
"""CLI operativa para gestionar plantas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_paths import get_project_paths
from mejoradora_plants import (
    OPTIONAL_PLANT_FIELDS,
    REQUIRED_PLANT_FIELDS,
    VALID_PLANT_STATUSES,
    add_plant,
    load_plants,
    set_plant_status,
    validate_plants,
)


PATHS = get_project_paths(Path(__file__))
PLANTS_FILE = PATHS.data / "plants.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestión operativa de plantas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Listar plantas")
    list_parser.add_argument("--status", choices=["all", *VALID_PLANT_STATUSES], default="all")
    list_parser.add_argument("--json", action="store_true", help="Salida JSON")

    active_parser = subparsers.add_parser("active", help="Listar solo plantas activas")
    active_parser.add_argument("--json", action="store_true", help="Salida JSON")

    add_parser = subparsers.add_parser("add", help="Añadir una planta")
    add_parser.add_argument("--plant-id", help="ID estable. Si no se indica, se genera desde el nombre")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--lat", required=True, type=float)
    add_parser.add_argument("--lon", required=True, type=float)
    add_parser.add_argument("--address", default="")
    add_parser.add_argument("--municipality", default="")
    add_parser.add_argument("--province", default="")
    add_parser.add_argument("--autonomous-community", default="")
    add_parser.add_argument("--postal-code", default="")
    add_parser.add_argument("--radio-km", type=float, default=2.0)
    add_parser.add_argument("--energy-available-kwh", type=float)
    add_parser.add_argument("--target-min-consumption-kwh-year", type=float)
    add_parser.add_argument("--solar-price-eur-kwh", type=float)
    add_parser.add_argument("--community-name", default="")
    add_parser.add_argument("--status", choices=VALID_PLANT_STATUSES, default="pending_data")
    add_parser.add_argument("--notes", default="")
    add_parser.add_argument("--power-kw", type=float)
    add_parser.add_argument("--surplus-percentage", type=float)

    status_parser = subparsers.add_parser("set-status", help="Cambiar estado de una planta")
    status_parser.add_argument("plant_id")
    status_parser.add_argument("status", choices=VALID_PLANT_STATUSES)
    status_parser.add_argument("--note", default="")

    subparsers.add_parser("validate", help="Validar el catálogo de plantas")
    return parser


def print_table(plants: list[dict]) -> None:
    rows = [
        [
            plant.get("plant_id", ""),
            plant.get("status", ""),
            plant.get("name", ""),
            str(plant.get("municipality", "") or "-"),
            str(plant.get("province", "") or "-"),
            str(plant.get("radio_km", "") or "-"),
        ]
        for plant in plants
    ]
    headers = ["plant_id", "status", "name", "municipality", "province", "radio_km"]
    widths = [len(header) for header in headers]

    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    print("  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command in {"list", "active"}:
        plants = load_plants(PLANTS_FILE)
        desired_status = "active" if args.command == "active" else args.status
        if desired_status != "all":
            plants = [plant for plant in plants if plant.get("status") == desired_status]
        if args.json:
            print(json.dumps(plants, ensure_ascii=False, indent=2))
        else:
            print_table(plants)
            print(f"\nTotal: {len(plants)} planta(s)")
        return 0

    if args.command == "add":
        plant = add_plant(
            PLANTS_FILE,
            {
                "plant_id": args.plant_id,
                "name": args.name,
                "lat": args.lat,
                "lon": args.lon,
                "address": args.address,
                "municipality": args.municipality,
                "province": args.province,
                "autonomous_community": args.autonomous_community,
                "postal_code": args.postal_code,
                "radio_km": args.radio_km,
                "energy_available_kwh": args.energy_available_kwh,
                "target_min_consumption_kwh_year": args.target_min_consumption_kwh_year,
                "solar_price_eur_kwh": args.solar_price_eur_kwh,
                "community_name": args.community_name,
                "status": args.status,
                "notes": args.notes,
                "power_kw": args.power_kw,
                "surplus_percentage": args.surplus_percentage,
            },
        )
        print(f"Planta añadida: {plant['plant_id']} [{plant['status']}] {plant['name']}")
        return 0

    if args.command == "set-status":
        plant = set_plant_status(PLANTS_FILE, args.plant_id, args.status, note=args.note)
        print(f"Estado actualizado: {plant['plant_id']} -> {plant['status']}")
        return 0

    if args.command == "validate":
        plants = load_plants(PLANTS_FILE)
        errors = validate_plants(plants)
        if errors:
            print("VALIDATION_ERRORS")
            for error in errors:
                print(f"- {error}")
            return 1

        print("VALIDATION_OK")
        print(f"required_fields={','.join(REQUIRED_PLANT_FIELDS)}")
        print(f"optional_fields={','.join(OPTIONAL_PLANT_FIELDS)}")
        print(f"plants={len(plants)}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
