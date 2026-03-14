#!/usr/bin/env python3
from crawl4ai import AsyncWebCrawler
import asyncio
import json
import re
import os

ENRICHED_PATH = os.path.expanduser("~/openfang/runs/enriched.json")
MAX_WEBS = 10
SLEEP_SECONDS = 1

MOBILE_REGEX = re.compile(r"(?<!\d)([67]\d{8})(?!\d)")
EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")


def load_enriched():
    if not os.path.exists(ENRICHED_PATH):
        return {}
    try:
        with open(ENRICHED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_enriched(data):
    os.makedirs(os.path.dirname(ENRICHED_PATH), exist_ok=True)
    with open(ENRICHED_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def has_spanish_mobile(phone):
    digits = re.sub(r"\D", "", str(phone or ""))
    if digits.startswith("34") and len(digits) >= 11:
        digits = digits[2:]
    return bool(MOBILE_REGEX.search(digits))


def pick_website(lead):
    if not isinstance(lead, dict):
        return ""
    return normalize_url(lead.get("website") or lead.get("web") or "")


def extract_from_markdown(markdown):
    text = str(markdown or "")

    mobiles = []
    seen_mobiles = set()
    for mobile in MOBILE_REGEX.findall(text):
        if mobile not in seen_mobiles:
            seen_mobiles.add(mobile)
            mobiles.append(mobile)

    emails = []
    seen_emails = set()
    for email in EMAIL_REGEX.findall(text):
        email_norm = email.lower()
        if email_norm not in seen_emails:
            seen_emails.add(email_norm)
            emails.append(email_norm)

    return mobiles, emails


def get_markdown(result):
    if result is None:
        return ""
    for attr in ("markdown", "fit_markdown", "raw_markdown"):
        value = getattr(result, attr, "")
        if value:
            return value
    return ""


async def process_lead(crawler, lead):
    website = pick_website(lead)
    if not website:
        return None, []

    result = await crawler.arun(url=website)
    markdown = get_markdown(result)
    return website, extract_from_markdown(markdown)


async def run():
    enriched = load_enriched()
    if not enriched:
        print("No hay datos en enriched.json")
        print("Resumen final: 0 leads con móvil nuevo encontrado")
        return

    candidates = []
    for lead_id, lead in enriched.items():
        if not isinstance(lead, dict):
            continue

        website = pick_website(lead)
        if not website:
            continue

        if has_spanish_mobile(lead.get("telefono", "")):
            continue

        candidates.append((lead_id, lead))
        if len(candidates) >= MAX_WEBS:
            break

    if not candidates:
        print("No hay leads pendientes con website y sin móvil.")
        print("Resumen final: 0 leads con móvil nuevo encontrado")
        return

    found_new_mobile = 0

    async with AsyncWebCrawler() as crawler:
        total = len(candidates)
        for index, (lead_id, lead) in enumerate(candidates, start=1):
            name = str(lead.get("name") or lead_id)
            print(f"[{index}/{total}] {name}")

            try:
                _, (mobiles, emails) = await process_lead(crawler, lead)
            except Exception as exc:
                print(f"  -> Error crawl: {exc}")
                mobiles, emails = [], []

            old_phone = str(lead.get("telefono") or "").strip()
            if mobiles:
                lead["telefono"] = mobiles[0]
                if not has_spanish_mobile(old_phone):
                    found_new_mobile += 1

            if emails:
                lead["email"] = emails[0]

            enriched[lead_id] = lead
            save_enriched(enriched)

            if index < total:
                await asyncio.sleep(SLEEP_SECONDS)

    print(f"Resumen final: {found_new_mobile} leads con móvil nuevo encontrado")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
