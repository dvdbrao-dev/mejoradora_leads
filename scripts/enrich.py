#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path
from urllib import error, parse, request

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_paths import get_project_paths
from mejoradora_runtime import iter_valid_run_records


PATHS = get_project_paths(Path(__file__))
RUNS_DIR = PATHS.runs
ENRICHED_PATH = RUNS_DIR / "enriched.json"
API_BASE = "https://places.googleapis.com/v1/places"
FIELD_MASK = "internationalPhoneNumber,websiteUri,regularOpeningHours,nationalPhoneNumber"
SLEEP_SECONDS = 0.3


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_enriched() -> dict:
    if not ENRICHED_PATH.exists():
        return {}

    try:
        data = load_json(ENRICHED_PATH)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_enriched(enriched: dict) -> None:
    ENRICHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ENRICHED_PATH.open("w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)


def get_tier(record: dict) -> str:
    if not isinstance(record, dict):
        return ""
    return str(record.get("tier") or record.get("paco", {}).get("tier") or "").strip().upper()


def get_place_id(record: dict) -> str:
    if not isinstance(record, dict):
        return ""

    lead = record.get("lead") if isinstance(record.get("lead"), dict) else {}

    place_id = (
        lead.get("place_id")
        or record.get("place_id")
        or lead.get("google_place_id")
        or record.get("google_place_id")
        or ""
    )

    return str(place_id).strip()


def get_name(record: dict) -> str:
    if not isinstance(record, dict):
        return ""

    lead = record.get("lead") if isinstance(record.get("lead"), dict) else {}
    name = lead.get("lead_name") or record.get("lead_name") or lead.get("name") or record.get("name") or ""
    return str(name).strip()


def build_candidates(enriched: dict):
    candidates = {}

    for path, record in iter_valid_run_records(RUNS_DIR):
        tier = get_tier(record)
        if tier not in {"A", "B"}:
            continue

        place_id = get_place_id(record)
        if not place_id or place_id in enriched:
            continue

        if place_id in candidates:
            continue

        name = get_name(record)
        candidates[place_id] = {
            "place_id": place_id,
            "name": name,
            "tier": tier,
        }

    return list(candidates.values())


def fetch_place_details(place_id: str, api_key: str) -> dict:
    safe_place_id = parse.quote(place_id, safe="")
    url = f"{API_BASE}/{safe_place_id}"

    req = request.Request(
        url=url,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        method="GET",
    )

    with request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def extract_horario(regular_opening_hours):
    if not isinstance(regular_opening_hours, dict):
        return []

    weekday_descriptions = regular_opening_hours.get("weekdayDescriptions")
    if isinstance(weekday_descriptions, list):
        return [str(item) for item in weekday_descriptions]

    return []


def main():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GOOGLE_PLACES_API_KEY en el entorno")

    enriched = load_enriched()
    candidates = build_candidates(enriched)

    total = len(candidates)
    if total == 0:
        print("No hay leads Tier A/B con place_id pendientes de enriquecer.")
        print("Resumen: 0/0 leads con teléfono, 0/0 con website")
        return

    print(f"Procesando {total} leads Tier A/B con place_id...")

    with_phone = 0
    with_website = 0

    for idx, lead in enumerate(candidates, start=1):
        place_id = lead["place_id"]
        name = lead["name"]
        tier = lead["tier"]

        print(f"[{idx}/{total}] {name or place_id} ({tier})")

        entry = {
            "name": name,
            "telefono": "",
            "website": "",
            "horario": [],
            "tier": tier,
        }

        try:
            details = fetch_place_details(place_id=place_id, api_key=api_key)
            entry["telefono"] = str(details.get("nationalPhoneNumber") or "").strip()
            entry["website"] = str(details.get("websiteUri") or "").strip()
            entry["horario"] = extract_horario(details.get("regularOpeningHours"))
        except error.HTTPError as exc:
            print(f"  -> HTTP {exc.code} al consultar place_id {place_id}")
        except error.URLError as exc:
            print(f"  -> Error de red para {place_id}: {exc.reason}")
        except (TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"  -> Error procesando {place_id}: {exc}")

        enriched[place_id] = entry
        save_enriched(enriched)

        if entry["telefono"]:
            with_phone += 1
        if entry["website"]:
            with_website += 1

        if idx < total:
            time.sleep(SLEEP_SECONDS)

    print(f"Resumen: {with_phone}/{total} leads con teléfono, {with_website}/{total} con website")


if __name__ == "__main__":
    main()
