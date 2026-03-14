#!/usr/bin/env python3
"""Scraper de Google Maps para entorno headless (Ubuntu VPS)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import urlopen


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "inputs" / "raw"
CSV_COLUMNS = [
    "lead_name",
    "sector",
    "address",
    "municipality",
    "province",
    "phone",
    "source",
    "notes",
]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower())
    return re.sub(r"_+", "_", clean).strip("_") or "valor"


def infer_sector(query: str) -> str:
    q = query.lower()
    if any(token in q for token in ("bar", "restaurante", "cafeteria", "cafetería")):
        return "hostelería"
    if "taller" in q:
        return "taller"
    return "otro"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def strip_postal_code(value: str) -> str:
    return re.sub(r"\b\d{4,6}\b", "", value).strip(" ,-;")


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


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def scrape_with_scrapling(query: str, zona: str, max_results: int, debug: bool = False) -> list[dict[str, str]]:
    from bs4 import BeautifulSoup  # type: ignore
    from patchright.sync_api import sync_playwright  # type: ignore

    search_term = f"{query} {zona}".strip()
    maps_url = f"https://www.google.com/maps/search/{quote_plus(search_term)}?hl=es"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )

        # Inyectar consentimiento antes de navegar para evitar consent.google.com.
        context.add_cookies(
            [
                {
                    "name": "SOCS",
                    "value": "CAISHAgBEhJnd3NfMjAyNDA0MDktMF9SQzIaAmVzIAEaBgiA_LKxBg",
                    "domain": ".google.com",
                    "path": "/",
                }
            ]
        )

        page = context.new_page()
        page.goto(maps_url, wait_until="domcontentloaded", timeout=30000)

        # Esperar feed.
        try:
            page.wait_for_selector('div[role="feed"]', timeout=20000)
        except Exception:
            pass

        # Scroll hasta max_results.
        for _ in range(max(12, max_results * 2)):
            count = page.locator('a[href*="/maps/place/"]').count()
            if count >= max_results:
                break
            try:
                page.locator('div[role="feed"]').first.evaluate("el => el.scrollTop = el.scrollHeight")
            except Exception:
                page.mouse.wheel(0, 2500)
            page.wait_for_timeout(random.randint(2000, 4000))

        html = page.content()
        browser.close()

    if debug:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        debug_path = RAW_DIR / f"debug_{timestamp}.html"
        debug_path.write_text(html, encoding="utf-8")
        print(f"🔍 HTML guardado en {debug_path}")

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('div.Nv2PK, div[role="article"]')
    if not cards:
        raise RuntimeError("No se encontraron tarjetas de resultados en el DOM renderizado")

    rows: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    for card in cards:
        name_from_qbf1pd = clean_text(
            card.select_one("div.qBF1Pd").get_text(" ", strip=True)
            if card.select_one("div.qBF1Pd")
            else ""
        )
        name_link = card.select_one("a.hfpxzc")
        name_from_link = clean_text(name_link.get("aria-label", "") if name_link else "")
        lead_name = clean_text(name_from_qbf1pd or name_from_link or "")

        block = card.select_one("div.W4Efsd div.W4Efsd")
        notes = ""
        address = ""
        if block:
            spans = block.select("span > span")
            clean_spans = [s for s in spans if not s.get("aria-hidden")]
            notes = clean_text(clean_spans[0].get_text()) if len(clean_spans) > 0 else ""
            address = clean_text(clean_spans[1].get_text()) if len(clean_spans) > 1 else ""

        card_text_parts: list[str] = []
        for span in card.select("span"):
            span_text = clean_text(span.get_text(" ", strip=True))
            if span_text:
                card_text_parts.append(span_text)
        card_text = " ".join(card_text_parts)
        phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", card_text)
        phone = clean_text(phone_match.group(0) if phone_match else "")

        if not lead_name:
            continue

        dedupe_key = (lead_name.lower(), address.lower())
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        municipality, province = infer_location(address, zona)
        row = {
            "lead_name": lead_name,
            "address": address,
            "municipality": municipality,
            "province": province,
            "phone": phone,
            "notes": notes,
            "source": "google_maps",
            "sector": "",
        }
        rows.append(row)

        idx = len(rows)
        display_place = municipality or zona
        print(f"✓ {idx}/{max_results} {lead_name} — {display_place}")

        if len(rows) >= max_results:
            break

    if not rows:
        raise RuntimeError("No se extrajeron resultados válidos con response.css() sobre tarjetas de lista.")

    return rows


def scrape_with_places_api(query: str, zona: str, max_results: int, api_key: str) -> list[dict[str, str]]:
    search_term = f"{query} {zona}".strip()
    rows: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    page_token = ""

    while len(rows) < max_results:
        token_query = f"&pagetoken={quote_plus(page_token)}" if page_token else ""
        url = (
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
            f"?query={quote_plus(search_term)}&language=es&region=es{token_query}&key={quote_plus(api_key)}"
        )
        with urlopen(url, timeout=30) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))

        results = payload.get("results", [])
        for place in results:
            lead_name = clean_text(place.get("name", ""))
            address = clean_text(place.get("formatted_address", ""))
            if not lead_name:
                continue

            key = (lead_name.lower(), address.lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)

            municipality, province = infer_location(address, zona)
            rows.append(
                {
                    "lead_name": lead_name,
                    "address": address,
                    "municipality": municipality,
                    "province": province,
                    "phone": "",
                    "notes": "",
                    "source": "google_places_api",
                    "sector": "",
                }
            )
            print(f"✓ {len(rows)}/{max_results} {lead_name} — {municipality or zona}")
            if len(rows) >= max_results:
                break

        if len(rows) >= max_results:
            break

        page_token = clean_text(payload.get("next_page_token", ""))
        if not page_token:
            break
        # La API tarda unos segundos en habilitar next_page_token.
        import time

        time.sleep(2)

    if not rows:
        raise RuntimeError("Places API no devolvió resultados válidos")
    return rows


def save_csv(rows: list[dict[str, str]], query: str, zona: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_query = slugify(query)
    safe_zona = slugify(zona)
    output_path = RAW_DIR / f"{safe_query}_{safe_zona}_{timestamp}.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean_text(row.get(col, "")) for col in CSV_COLUMNS})

    return output_path


def main() -> int:
    load_env_file(BASE_DIR / ".env")

    parser = argparse.ArgumentParser(description="Scraper de Google Maps para Openfang")
    parser.add_argument("--query", required=True, help="Búsqueda, por ejemplo: bares")
    parser.add_argument("--zona", required=True, help="Zona, por ejemplo: Granada, España")
    parser.add_argument("--max", type=int, default=50, dest="max_results", help="Máximo de resultados")
    parser.add_argument("--debug", action="store_true", help="Guardar HTML completo de la página en inputs/raw")
    args = parser.parse_args()

    if args.max_results <= 0:
        print("❌ --max debe ser mayor que 0", file=sys.stderr)
        return 1

    sector = infer_sector(args.query)

    rows: list[dict[str, str]] = []
    try:
        rows = scrape_with_scrapling(args.query, args.zona, args.max_results, debug=args.debug)
    except Exception as exc:
        print(f"⚠️ Scraping web falló: {exc}", file=sys.stderr)
        api_key = clean_text(os.getenv("GOOGLE_PLACES_API_KEY", ""))
        if not api_key:
            print(
                "❌ No se encontró GOOGLE_PLACES_API_KEY. "
                "Define la variable de entorno para usar fallback con Places API.",
                file=sys.stderr,
            )
            return 2
        try:
            print("ℹ️ Intentando fallback con Google Places API...", file=sys.stderr)
            rows = scrape_with_places_api(args.query, args.zona, args.max_results, api_key)
        except Exception as api_exc:
            print(f"❌ Fallback Places API falló: {api_exc}", file=sys.stderr)
            return 2

    for row in rows:
        row["sector"] = sector

    rows = dedupe_rows(rows)
    rows = rows[: args.max_results]

    output_path = save_csv(rows, args.query, args.zona)
    print(f"✅ CSV guardado: {output_path}")
    print(f"OUTPUT_CSV={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
