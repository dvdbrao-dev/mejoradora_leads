#!/usr/bin/env python3
"""Registro operativo de plantas para Mejoradora Leads."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_PLANT_STATUSES = ("active", "full", "paused", "pending_data", "archived")
DEFAULT_RADIO_KM = 2.0

REQUIRED_PLANT_FIELDS = (
    "plant_id",
    "name",
    "lat",
    "lon",
    "radio_km",
    "status",
    "created_at",
    "updated_at",
)

OPTIONAL_PLANT_FIELDS = (
    "address",
    "municipality",
    "province",
    "autonomous_community",
    "postal_code",
    "energy_available_kwh",
    "target_min_consumption_kwh_year",
    "solar_price_eur_kwh",
    "community_name",
    "notes",
    "power_kw",
    "surplus_percentage",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower())
    return re.sub(r"_+", "_", clean).strip("_") or "plant"


def to_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_raw_plants(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    plants = payload.get("plants")
    if isinstance(plants, list):
        return [item for item in plants if isinstance(item, dict)]
    solar_plants = payload.get("solar_plants")
    if isinstance(solar_plants, list):
        return [item for item in solar_plants if isinstance(item, dict)]
    return []


def _normalize_plant(raw: dict[str, Any], index: int) -> dict[str, Any]:
    coords = raw.get("coordinates") if isinstance(raw.get("coordinates"), dict) else {}
    lat = raw.get("lat", coords.get("latitude"))
    lon = raw.get("lon", coords.get("longitude"))
    name = clean_text(raw.get("name")) or f"Planta {index}"
    legacy_id = clean_text(raw.get("plant_id") or raw.get("id"))
    plant_id = legacy_id or f"plant_{index}"

    created_at = clean_text(raw.get("created_at"))
    updated_at = clean_text(raw.get("updated_at"))

    return {
        "plant_id": plant_id,
        "name": name,
        "lat": to_float(lat),
        "lon": to_float(lon),
        "address": clean_text(raw.get("address")),
        "municipality": clean_text(raw.get("municipality")),
        "province": clean_text(raw.get("province")),
        "autonomous_community": clean_text(raw.get("autonomous_community")),
        "postal_code": clean_text(raw.get("postal_code")),
        "radio_km": to_float(raw.get("radio_km")) or DEFAULT_RADIO_KM,
        "energy_available_kwh": to_float(raw.get("energy_available_kwh")),
        "target_min_consumption_kwh_year": to_float(raw.get("target_min_consumption_kwh_year")),
        "solar_price_eur_kwh": to_float(raw.get("solar_price_eur_kwh")),
        "community_name": clean_text(raw.get("community_name")),
        "status": clean_text(raw.get("status")).lower() or "active",
        "notes": clean_text(raw.get("notes")),
        "created_at": created_at,
        "updated_at": updated_at,
        "power_kw": to_float(raw.get("power_kw")),
        "surplus_percentage": to_float(raw.get("surplus_percentage")),
    }


def load_plants(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [_normalize_plant(raw, idx) for idx, raw in enumerate(_extract_raw_plants(payload), start=1)]


def validate_plants(plants: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}

    for idx, plant in enumerate(plants, start=1):
        plant_id = clean_text(plant.get("plant_id"))
        if not plant_id:
            errors.append(f"Planta #{idx}: falta plant_id")
        elif plant_id in seen:
            errors.append(f"Duplicado plant_id='{plant_id}' en posiciones {seen[plant_id]} y {idx}")
        else:
            seen[plant_id] = idx

        if not clean_text(plant.get("name")):
            errors.append(f"Planta #{idx}: falta name")
        if to_float(plant.get("lat")) is None:
            errors.append(f"Planta #{idx}: lat inválido")
        if to_float(plant.get("lon")) is None:
            errors.append(f"Planta #{idx}: lon inválido")
        if to_float(plant.get("radio_km")) is None or float(plant["radio_km"]) <= 0:
            errors.append(f"Planta #{idx}: radio_km debe ser > 0")

        status = clean_text(plant.get("status")).lower()
        if status not in VALID_PLANT_STATUSES:
            errors.append(f"Planta #{idx}: status inválido '{status}'")

        if not clean_text(plant.get("created_at")):
            errors.append(f"Planta #{idx}: falta created_at")
        if not clean_text(plant.get("updated_at")):
            errors.append(f"Planta #{idx}: falta updated_at")

    return errors


def save_plants(path: Path, plants: list[dict[str, Any]]) -> None:
    normalized = [_normalize_plant(plant, idx) for idx, plant in enumerate(plants, start=1)]
    errors = validate_plants(normalized)
    if errors:
        raise ValueError("\n".join(errors))

    payload = {
        "version": 1,
        "source": "official_plant_registry",
        "updated_at": utc_now(),
        "plants": normalized,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_active_plant_ids(path: Path) -> set[str]:
    return {plant["plant_id"] for plant in load_plants(path) if plant.get("status") == "active"}


def load_capture_plants(path: Path, min_surplus: float | None = None) -> list[dict[str, Any]]:
    plants: list[dict[str, Any]] = []
    for plant in load_plants(path):
        if plant.get("status") != "active":
            continue

        surplus = to_float(plant.get("surplus_percentage"))
        if min_surplus is not None and min_surplus > 0:
            if surplus is None or surplus < min_surplus:
                continue

        plants.append(
            {
                "plant_id": clean_text(plant.get("plant_id")),
                "plant_name": clean_text(plant.get("name")),
                "plant_power_kw": clean_text(plant.get("power_kw")),
                "plant_surplus_pct": surplus if surplus is not None else 0.0,
                "latitude": float(plant["lat"]),
                "longitude": float(plant["lon"]),
                "radio_km": float(plant["radio_km"]),
                "status": clean_text(plant.get("status")),
            }
        )
    return plants


def load_dashboard_plants(path: Path, status: str | None = "active") -> list[dict[str, Any]]:
    plants: list[dict[str, Any]] = []
    for plant in load_plants(path):
        plant_status = clean_text(plant.get("status")).lower()
        if status and plant_status != status:
            continue
        plants.append(
            {
                "id": plant["plant_id"],
                "name": plant["name"],
                "latitude": plant["lat"],
                "longitude": plant["lon"],
                "surplus": plant.get("surplus_percentage"),
                "power_kw": plant.get("power_kw"),
                "status": plant_status,
                "municipality": plant.get("municipality"),
                "province": plant.get("province"),
                "radio_km": plant.get("radio_km"),
            }
        )
    return plants


def add_plant(path: Path, raw_plant: dict[str, Any]) -> dict[str, Any]:
    plants = load_plants(path)
    now = utc_now()
    plant = _normalize_plant(raw_plant, len(plants) + 1)
    plant["plant_id"] = clean_text(raw_plant.get("plant_id")) or slugify(plant["name"])
    plant["created_at"] = now
    plant["updated_at"] = now
    if not clean_text(raw_plant.get("status")):
        plant["status"] = "pending_data"
    plants.append(plant)
    save_plants(path, plants)
    return plant


def set_plant_status(path: Path, plant_id: str, status: str, note: str = "") -> dict[str, Any]:
    normalized_status = clean_text(status).lower()
    if normalized_status not in VALID_PLANT_STATUSES:
        raise ValueError(f"status inválido: {status}")

    plants = load_plants(path)
    needle = clean_text(plant_id).lower()
    now = utc_now()

    for plant in plants:
        if clean_text(plant.get("plant_id")).lower() != needle:
            continue
        plant["status"] = normalized_status
        plant["updated_at"] = now
        if clean_text(note):
            current_notes = clean_text(plant.get("notes"))
            plant["notes"] = f"{current_notes} | {clean_text(note)}" if current_notes else clean_text(note)
        save_plants(path, plants)
        return plant

    raise ValueError(f"No existe plant_id='{plant_id}'")
