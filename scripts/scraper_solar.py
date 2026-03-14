#!/usr/bin/env python3
"""Scraper de clientes próximos a plantas fotovoltaicas con Google Places API (New)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "inputs" / "raw"
CSV_COLUMNS = [
    "lead_name",
    "place_id",
    "sector",
    "address",
    "municipality",
    "province",
    "phone",
    "website",
    "source",
    "notes",
    "plant_id",
    "plant_name",
    "plant_power_kw",
    "plant_surplus_pct",
    "distance_km",
]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower())
    return re.sub(r"_+", "_", clean).strip("_") or "valor"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def strip_postal_code(value: str) -> str:
    return re.sub(r"\b\d{4,6}\b", "", value).strip(" ,;-")


def infer_location(address: str, zona: str) -> tuple[str, str]:
    text = clean_text(address)
    if not text:
        return "", ""

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return "", ""

    normalized_zone = {x.strip().lower() for x in zona.split(",") if x.strip()}

    # Quitar país si viene al final.
    if parts and parts[-1].lower() in {"españa", "spain"}:
        parts = parts[:-1]

    province = ""
    municipality = ""

    if len(parts) >= 1:
        candidate = strip_postal_code(parts[-1])
        if candidate and candidate.lower() not in normalized_zone:
            province = candidate

    if len(parts) >= 2:
        candidate = strip_postal_code(parts[-2])
        if candidate:
            municipality = candidate

    # Ajuste común: si sólo tenemos una localidad clara, usarla como municipio.
    if not municipality and len(parts) >= 1:
        maybe_city = strip_postal_code(parts[-1])
        if maybe_city and maybe_city.lower() not in {"granada", "andalucia", "andalucía"}:
            municipality = maybe_city

    return municipality, province


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = (clean_text(row.get("lead_name", "")).lower(), clean_text(row.get("address", "")).lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def save_csv(rows: list[dict[str, str]]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = RAW_DIR / f"solar_{timestamp}.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean_text(row.get(col, "")) for col in CSV_COLUMNS})

    return output_path


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def infer_sector_from_primary_type(primary_type_display_name: Any) -> str:
    primary = ""
    if isinstance(primary_type_display_name, dict):
        primary = clean_text(primary_type_display_name.get("text", "")).lower()
    else:
        primary = clean_text(primary_type_display_name).lower()

    if any(token in primary for token in ("restaurant", "bar", "cafe", "lodging")):
        return "hostelería"
    if "car repair" in primary:
        return "taller"
    if "city hall" in primary:
        return "ayuntamiento"
    if any(token in primary for token in ("store", "supermarket")):
        return "comercio"
    if "factory" in primary:
        return "industria"
    return "otro"


def fetch_nearby_places(api_key: str, latitude: float, longitude: float, radius: int, max_results: int) -> list[dict[str, Any]]:
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.name,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.primaryTypeDisplayName,"
            "places.location,places.websiteUri"
        ),
    }
    payload = {
        "includedTypes": [
            "restaurant",
            "bar",
            "cafe",
            "store",
            "car_repair",
            "city_hall",
            "lodging",
            "supermarket",
            "storage",
        ],
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius),
            }
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("places", [])


def load_plants(path: Path, min_surplus: float) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    plants = payload.get("solar_plants", [])
    out: list[dict[str, Any]] = []

    for idx, plant in enumerate(plants, start=1):
        coordinates = plant.get("coordinates", {})
        lat = coordinates.get("latitude")
        lng = coordinates.get("longitude")
        if lat is None or lng is None:
            continue

        surplus = float(plant.get("surplus_percentage", 0) or 0)
        if surplus < min_surplus:
            continue

        out.append(
            {
                "plant_id": clean_text(plant.get("id", "")) or f"plant_{idx}",
                "plant_name": clean_text(plant.get("name", "")) or f"Planta {idx}",
                "plant_power_kw": clean_text(plant.get("power_kw", "")),
                "plant_surplus_pct": surplus,
                "latitude": float(lat),
                "longitude": float(lng),
            }
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Scraper solar con Google Places API (New)")
    parser.add_argument("--plants", required=True, help="Path al JSON de plantas")
    parser.add_argument("--api-key", required=True, help="Google Places API key")
    parser.add_argument("--radius", type=int, default=2000, help="Radio en metros")
    parser.add_argument("--max-per-plant", type=int, default=20, help="Máximo de leads por planta")
    parser.add_argument(
        "--min-surplus",
        type=float,
        default=0,
        help="Filtrar plantas con surplus_percentage menor a este valor",
    )
    args = parser.parse_args()

    if args.radius <= 0:
        print("❌ --radius debe ser mayor que 0", file=sys.stderr)
        return 1
    if args.max_per_plant <= 0:
        print("❌ --max-per-plant debe ser mayor que 0", file=sys.stderr)
        return 1

    plants_path = Path(args.plants)
    if not plants_path.exists():
        print(f"❌ No existe el archivo de plantas: {plants_path}", file=sys.stderr)
        return 1

    plants = load_plants(plants_path, args.min_surplus)
    if not plants:
        print("⚠️ No hay plantas que cumplan el filtro de excedente.")
        return 0

    grouped: dict[tuple[float, float], list[dict[str, Any]]] = {}
    for plant in plants:
        key = (plant["latitude"], plant["longitude"])
        grouped.setdefault(key, []).append(plant)

    best_by_business: dict[tuple[str, str], dict[str, str]] = {}
    for (lat, lng), plants_in_location in grouped.items():
        chosen_plant = max(plants_in_location, key=lambda p: float(p["plant_surplus_pct"]))
        print(
            "🌞 Procesando "
            f"{chosen_plant['plant_name']} ({float(chosen_plant['plant_surplus_pct']):.1f}% excedente) "
            f"— {len(plants_in_location)} plantas en esta ubicación"
        )

        try:
            places = fetch_nearby_places(
                api_key=args.api_key,
                latitude=lat,
                longitude=lng,
                radius=args.radius,
                max_results=args.max_per_plant,
            )
        except Exception as exc:
            print(f"⚠️ Error consultando Places API para {chosen_plant['plant_name']}: {exc}", file=sys.stderr)
            continue

        idx = 0
        for place in places:
            place_name = clean_text(place.get("name", ""))
            place_id = place_name.split("/")[-1] if place_name else ""
            display_name = place.get("displayName", {})
            lead_name = clean_text(display_name.get("text", "") if isinstance(display_name, dict) else display_name)
            if not lead_name:
                continue

            address = clean_text(place.get("formattedAddress", ""))
            municipality, province = infer_location(address, "")
            phone = clean_text(place.get("nationalPhoneNumber", ""))
            website = clean_text(place.get("websiteUri", ""))
            notes_obj = place.get("primaryTypeDisplayName", {})
            notes = clean_text(notes_obj.get("text", "") if isinstance(notes_obj, dict) else notes_obj)
            sector = infer_sector_from_primary_type(notes_obj)

            place_location = place.get("location", {}) or {}
            place_lat = place_location.get("latitude")
            place_lng = place_location.get("longitude")
            if place_lat is None or place_lng is None:
                distance_km = ""
                distance_float = float("inf")
            else:
                distance_float = haversine_km(float(place_lat), float(place_lng), lat, lng)
                distance_km = f"{distance_float:.3f}"

            row = {
                "lead_name": lead_name,
                "place_id": place_id,
                "sector": sector,
                "address": address,
                "municipality": municipality,
                "province": province,
                "phone": phone,
                "website": website,
                "source": "google_maps_solar",
                "notes": notes,
                "plant_id": clean_text(chosen_plant["plant_id"]),
                "plant_name": clean_text(chosen_plant["plant_name"]),
                "plant_power_kw": clean_text(chosen_plant["plant_power_kw"]),
                "plant_surplus_pct": f"{float(chosen_plant['plant_surplus_pct']):.2f}",
                "distance_km": distance_km,
            }

            dedupe_key = (lead_name.lower(), address.lower())
            current = best_by_business.get(dedupe_key)
            if current is None:
                best_by_business[dedupe_key] = row
            else:
                current_surplus = float(clean_text(current.get("plant_surplus_pct", "0")) or 0)
                new_surplus = float(clean_text(row.get("plant_surplus_pct", "0")) or 0)
                if new_surplus > current_surplus:
                    best_by_business[dedupe_key] = row

            idx += 1
            printable_distance = f"{distance_float:.1f}km" if distance_float != float("inf") else "n/d"
            print(f"  ✓ {idx}/{args.max_per_plant} {lead_name} — {printable_distance}")
            if idx >= args.max_per_plant:
                break

    rows = list(best_by_business.values())
    rows = dedupe_rows(rows)
    output_path = save_csv(rows)
    print(f"✅ CSV guardado: {output_path}")
    print(f"OUTPUT_CSV={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
