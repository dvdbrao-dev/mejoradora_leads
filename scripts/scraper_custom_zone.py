#!/usr/bin/env python3
"""Scraper de leads en una zona manual con Google Places API (New)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(BASE_DIR))
from scraper_solar import (  # noqa: E402
    CSV_COLUMNS,
    DEFAULT_INCLUDED_TYPES,
    clean_text,
    fetch_nearby_places,
    haversine_km,
    infer_location,
    infer_sector_from_primary_type as classify_sector,
    slugify,
)


RAW_DIR = BASE_DIR / "inputs" / "raw"
PLANTS_PATH = BASE_DIR / "data" / "plants.json"


def load_plant(plant_id: str | None) -> dict[str, Any]:
    if not plant_id:
        return {
            "plant_id": "zona_custom",
            "plant_name": "",
            "plant_power_kw": "",
            "plant_surplus_pct": "",
        }

    payload = json.loads(PLANTS_PATH.read_text(encoding="utf-8"))
    plants = payload.get("plants", []) if isinstance(payload, dict) else []
    for plant in plants:
        if clean_text(plant.get("plant_id")) == clean_text(plant_id):
            surplus = plant.get("surplus_percentage")
            return {
                "plant_id": clean_text(plant.get("plant_id")),
                "plant_name": clean_text(plant.get("name")),
                "plant_power_kw": clean_text(plant.get("power_kw")),
                "plant_surplus_pct": "" if surplus is None else clean_text(surplus),
            }

    raise ValueError(f"No existe plant_id='{plant_id}' en {PLANTS_PATH}")


def save_csv(rows: list[dict[str, str]]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = RAW_DIR / f"custom_{timestamp}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean_text(row.get(col, "")) for col in CSV_COLUMNS})

    return output_path.resolve()


def place_to_row(place: dict[str, Any], lat: float, lng: float, plant: dict[str, Any]) -> dict[str, str] | None:
    place_name = clean_text(place.get("name", ""))
    place_id = place_name.split("/")[-1] if place_name else ""

    display_name = place.get("displayName", {})
    lead_name = clean_text(display_name.get("text", "") if isinstance(display_name, dict) else display_name)
    if not lead_name:
        return None

    address = clean_text(place.get("formattedAddress", ""))
    municipality, province = infer_location(address, "")
    phone = clean_text(place.get("nationalPhoneNumber", ""))
    website = clean_text(place.get("websiteUri", ""))
    notes_obj = place.get("primaryTypeDisplayName", {})
    notes = clean_text(notes_obj.get("text", "") if isinstance(notes_obj, dict) else notes_obj)

    place_location = place.get("location", {}) or {}
    place_lat = place_location.get("latitude")
    place_lng = place_location.get("longitude")
    distance_km = ""
    if place_lat is not None and place_lng is not None:
        distance_km = f"{haversine_km(float(place_lat), float(place_lng), lat, lng):.3f}"

    return {
        "lead_name": lead_name,
        "place_id": place_id,
        "sector": classify_sector(notes_obj),
        "address": address,
        "municipality": municipality,
        "province": province,
        "phone": phone,
        "website": website,
        "source": "google_maps_custom_zone",
        "notes": notes,
        "plant_id": plant["plant_id"],
        "plant_name": plant["plant_name"],
        "plant_power_kw": plant["plant_power_kw"],
        "plant_surplus_pct": plant["plant_surplus_pct"],
        "distance_km": distance_km,
    }


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (
            clean_text(row.get("place_id", "")).lower(),
            clean_text(row.get("lead_name", "")).lower(),
            clean_text(row.get("address", "")).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Scraper de leads en zona custom")
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lng", required=True, type=float)
    parser.add_argument("--radius-km", required=True, type=float)
    parser.add_argument("--plant-id", default="")
    args = parser.parse_args()

    if args.radius_km <= 0:
        print("ERROR: --radius-km debe ser mayor que 0", file=sys.stderr)
        return 1

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("ERROR: falta GOOGLE_PLACES_API_KEY", file=sys.stderr)
        return 1

    try:
        plant = load_plant(args.plant_id)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rows: list[dict[str, str]] = []
    radius_m = int(args.radius_km * 1000)
    try:
        places = fetch_nearby_places(
            api_key=api_key,
            latitude=args.lat,
            longitude=args.lng,
            radius=radius_m,
            max_results=20,
            included_types=DEFAULT_INCLUDED_TYPES,
        )
    except Exception as exc:
        print(f"ERROR: Google Places API: {exc}", file=sys.stderr)
        return 1

    zone_slug = slugify(f"{args.lat}_{args.lng}")
    print(f"Zona custom {zone_slug}: {len(places)} place(s)")

    for place in places:
        row = place_to_row(place, args.lat, args.lng, plant)
        if row is not None:
            rows.append(row)

    output_path = save_csv(dedupe_rows(rows))
    print(f"OUTPUT_CSV={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
