#!/usr/bin/env python3
"""Geocodifica leads en runs/*.json usando Google Places API.

Idempotente: omite leads que ya tengan lat/lng.
Añade: lat, lng, geocoded_at al dict ``lead``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


GOOGLE_API_KEY = (os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
RUNS_DIR = Path("runs")
RATE_LIMIT_SECONDS = 0.1
SKIP_FILES = {"enriched.json", "lead_status.json", "whatsapp_sent.json", "custom_searches.json"}


def has_coords(lead: dict[str, Any]) -> bool:
    return lead.get("lat") is not None and lead.get("lng") is not None


def geocode(address: str, name: str = "") -> tuple[float, float] | None:
    """Devuelve (lat, lng) usando Places API v1 o None si falla."""
    if not GOOGLE_API_KEY:
        print("⚠️ No hay GOOGLE_PLACES_API_KEY ni GOOGLE_API_KEY en entorno", file=sys.stderr)
        return None

    query = " ".join(part for part in (name.strip(), address.strip()) if part).strip()
    if not query:
        return None

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.location",
    }
    payload = {"textQuery": query, "languageCode": "es"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        places = data.get("places", [])
        if not places:
            return None
        location = places[0].get("location") or {}
        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)
    except Exception as exc:
        print(f"  ⚠️ geocoding error para '{query}': {exc}", file=sys.stderr)
        return None


def process_file(fp: Path) -> str:
    """Devuelve 'done', 'skipped' o 'failed'."""
    try:
        with fp.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(f"❌ {fp.name}: {exc}")
        return "failed"

    lead = data.get("lead")
    if not isinstance(lead, dict):
        return "failed"

    if has_coords(lead):
        return "skipped"

    address = str(lead.get("address") or lead.get("formatted_address") or "").strip()
    name = str(lead.get("lead_name") or lead.get("name") or data.get("lead_name") or "").strip()
    if not address:
        return "failed"

    coords = geocode(address, name=name)
    if not coords:
        return "failed"

    lead["lat"] = coords[0]
    lead["lng"] = coords[1]
    lead["geocoded_at"] = datetime.now(timezone.utc).isoformat()
    data["lead"] = lead

    with fp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    time.sleep(RATE_LIMIT_SECONDS)
    return "done"


def iter_run_files() -> list[Path]:
    return [fp for fp in sorted(RUNS_DIR.glob("*.json")) if fp.name not in SKIP_FILES]


def main() -> None:
    files = iter_run_files()
    if not files:
        raise SystemExit("No hay archivos válidos en runs/")

    counts = {"done": 0, "skipped": 0, "failed": 0}
    print(f"Procesando {len(files)} archivos...")

    for idx, fp in enumerate(files, start=1):
        result = process_file(fp)
        counts[result] += 1
        if idx % 50 == 0:
            print(
                f"  [{idx}/{len(files)}] "
                f"done={counts['done']} skipped={counts['skipped']} failed={counts['failed']}"
            )

    print("\n=== RESUMEN ===")
    for key in ("done", "skipped", "failed"):
        print(f"  {key}: {counts[key]}")


if __name__ == "__main__":
    main()
