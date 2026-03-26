#!/usr/bin/env python3
"""Scraper de leads por zona custom con Google Places API (New)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "inputs" / "raw"
PLANTS_FILE = BASE_DIR / "data" / "plants.json"
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

PLACE_TYPES = [
    "restaurant",
    "bar",
    "cafe",
    "store",
    "car_repair",
    "city_hall",
    "lodging",
    "supermarket",
    "storage",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower())
    return re.sub(r"_+", "_", clean).strip("_") or "valor"


def strip_postal_code(value: str) -> str:
    return re.sub(r"\b\d{4,6}\b", "", value).strip(" ,;-")


def infer_location(address: str) -> tuple[str, str]:
    text = clean_text(address)
    if not text:
        return "", ""

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return "", ""

    if parts and parts[-1].lower() in {"españa", "spain"}:
        parts = parts[:-1]

    province = strip_postal_code(parts[-1]) if len(parts) >= 1 else ""
    municipality = strip_postal_code(parts[-2]) if len(parts) >= 2 else ""

    if not municipality and parts:
        municipality = strip_postal_code(parts[-1])

    return municipality, province


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


def load_plants(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_plants = payload.get("solar_plants", [])
    plants: list[dict[str, Any]] = []

    for idx, plant in enumerate(raw_plants, start=1):
        if not isinstance(plant, dict):
            continue

        coords = plant.get("coordinates") or {}
        lat = coords.get("latitude")
        lng = coords.get("longitude")
        if lat is None or lng is None:
            continue

        name = clean_text(plant.get("name", "")) or f"Planta {idx}"
        raw_id = clean_text(plant.get("id", ""))
        plant_id = raw_id or f"{slugify(name)}_{idx}"

        plants.append(
            {
                "plant_id": plant_id,
                "plant_name": name,
                "plant_power_kw": clean_text(plant.get("power_kw", "")),
                "plant_surplus_pct": float(plant.get("surplus_percentage", 0) or 0),
                "latitude": float(lat),
                "longitude": float(lng),
            }
        )

    return plants


def find_assigned_plant(plants: list[dict[str, Any]], lat: float, lng: float, plant_id: str | None) -> dict[str, Any]:
    if not plants:
        raise ValueError("No hay plantas válidas en data/plants.json")

    if plant_id:
        needle = clean_text(plant_id).lower()
        for plant in plants:
            if plant["plant_id"].lower() == needle or plant["plant_name"].lower() == needle:
                return plant
        raise ValueError(f"No se encontró la planta solicitada: {plant_id}")

    return min(plants, key=lambda p: haversine_km(lat, lng, p["latitude"], p["longitude"]))


def geocode_address(api_key: str, address: str) -> tuple[float, float]:
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.location",
    }
    payload = {"textQuery": address, "maxResultCount": 1}

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    places = response.json().get("places", [])
    if not places:
        raise ValueError(f"No se pudo geocodificar la dirección: {address}")

    location = places[0].get("location") or {}
    lat = location.get("latitude")
    lng = location.get("longitude")
    if lat is None or lng is None:
        raise ValueError(f"Resultado sin coordenadas para dirección: {address}")

    return float(lat), float(lng)


def fetch_nearby_places(api_key: str, lat: float, lng: float, radius_km: float) -> list[dict[str, Any]]:
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
        "includedTypes": PLACE_TYPES,
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_km) * 1000,
            }
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json().get("places", [])


def save_csv(rows: list[dict[str, str]]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = RAW_DIR / f"custom_ZONE_{timestamp}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean_text(row.get(col, "")) for col in CSV_COLUMNS})

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper custom por zona")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lng", type=float)
    parser.add_argument("--radius-km", type=float, default=2.0)
    parser.add_argument("--plant-id", type=str)
    parser.add_argument("--address", type=str)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.radius_km <= 0:
        print("❌ --radius-km debe ser mayor que 0", file=sys.stderr)
        return 1

    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "tu api aqui perro")
    if not api_key or api_key == "tu api aqui perro":
        print("❌ Falta GOOGLE_PLACES_API_KEY en entorno", file=sys.stderr)
        return 1

    lat = args.lat
    lng = args.lng

    if args.address:
        try:
            lat, lng = geocode_address(api_key, args.address)
            print(f"📍 Dirección geocodificada: {args.address} -> {lat:.6f}, {lng:.6f}")
        except Exception as exc:
            print(f"❌ Error geocodificando dirección: {exc}", file=sys.stderr)
            return 1
    elif lat is None or lng is None:
        print("❌ Debes pasar --lat y --lng o --address", file=sys.stderr)
        return 1

    plants_path = PLANTS_FILE
    if not plants_path.exists():
        print(f"❌ No existe {plants_path}", file=sys.stderr)
        return 1

    try:
        plants = load_plants(plants_path)
        assigned_plant = find_assigned_plant(plants, float(lat), float(lng), args.plant_id)
    except Exception as exc:
        print(f"❌ Error cargando/asignando planta: {exc}", file=sys.stderr)
        return 1

    print(
        "🌞 Planta asignada: "
        f"{assigned_plant['plant_name']} (id={assigned_plant['plant_id']})"
    )

    try:
        places = fetch_nearby_places(api_key, float(lat), float(lng), args.radius_km)
    except Exception as exc:
        print(f"❌ Error consultando Places Nearby Search: {exc}", file=sys.stderr)
        return 1

    deduped_by_place_id: dict[str, dict[str, str]] = {}
    fallback_idx = 0

    for place in places:
        place_name_path = clean_text(place.get("name", ""))
        place_id = place_name_path.split("/")[-1] if place_name_path else ""
        if not place_id:
            fallback_idx += 1
            place_id = f"no_place_id_{fallback_idx}"

        display_name = place.get("displayName", {})
        lead_name = clean_text(display_name.get("text", "") if isinstance(display_name, dict) else display_name)
        if not lead_name:
            continue

        address = clean_text(place.get("formattedAddress", ""))
        municipality, province = infer_location(address)
        phone = clean_text(place.get("nationalPhoneNumber", ""))
        website = clean_text(place.get("websiteUri", ""))
        notes_obj = place.get("primaryTypeDisplayName", {})
        notes = clean_text(notes_obj.get("text", "") if isinstance(notes_obj, dict) else notes_obj)
        sector = infer_sector_from_primary_type(notes_obj)

        place_location = place.get("location") or {}
        p_lat = place_location.get("latitude")
        p_lng = place_location.get("longitude")
        if p_lat is None or p_lng is None:
            distance_km = ""
        else:
            distance_km = f"{haversine_km(float(p_lat), float(p_lng), assigned_plant['latitude'], assigned_plant['longitude']):.3f}"

        deduped_by_place_id[place_id] = {
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
            "plant_id": clean_text(assigned_plant["plant_id"]),
            "plant_name": clean_text(assigned_plant["plant_name"]),
            "plant_power_kw": clean_text(assigned_plant["plant_power_kw"]),
            "plant_surplus_pct": f"{float(assigned_plant['plant_surplus_pct']):.2f}",
            "distance_km": distance_km,
        }

    rows = list(deduped_by_place_id.values())
    output_path = save_csv(rows)
    print(f"✅ CSV guardado: {output_path}")
    print(f"OUTPUT_CSV={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
