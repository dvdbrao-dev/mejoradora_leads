#!/usr/bin/env python3
"""SMS engine para Mejoradora Leads usando la API HTTP de Dinahosting."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_contact_queue import build_contact_queue_from_runs
from mejoradora_paths import get_project_paths


DINAHOSTING_USER = os.environ.get("DINAHOSTING_USER", "").strip()
DINAHOSTING_PASS = os.environ.get("DINAHOSTING_PASS", "").strip()
DINAHOSTING_ACCOUNT = os.environ.get("DINAHOSTING_ACCOUNT", "").strip()
DINAHOSTING_ENDPOINT = "https://dinahosting.com/special/api.php"

SMS_COOLDOWN_SECONDS = 30
MAX_SMS_PER_SESSION = 50

SMS_TEMPLATES = {
    "A": "Hay energia solar a {distance} de {name}. 0,09 EUR/kWh sin inversion. WhatsApp 613685560 para info.",
    "B": "Pagas +300 EUR/mes luz en {name}? Energia solar cerca, 0,09 EUR/kWh. WhatsApp 613685560 para saber mas.",
}

PATHS = get_project_paths(Path(__file__))
SMS_LOG = PATHS.data / "logs" / "sms_sent.jsonl"


def normalize_phone(phone: str | None) -> str | None:
    """Normaliza telefono español a formato +34XXXXXXXXX."""
    if not phone:
        return None

    digits = "".join(char for char in str(phone) if char.isdigit())
    if digits.startswith("34") and len(digits) == 11:
        return f"+{digits}"
    if len(digits) == 9 and digits[0] in {"6", "7", "9"}:
        return f"+34{digits}"
    return None


def _safe_name(value: str | None) -> str:
    name = " ".join(str(value or "").strip().split())
    return name or "tu negocio"


def _distance_label(distance_km: float | None) -> str:
    if distance_km is None:
        return "muy cerca"
    return f"{distance_km:.1f}km"


def _fallback_message(lead: dict[str, Any], tier: str) -> str:
    template = SMS_TEMPLATES.get(tier, SMS_TEMPLATES["B"])
    message = template.format(
        name=_safe_name(lead.get("lead_name")),
        distance=_distance_label(lead.get("distance_km")),
    )
    if len(message) <= 160:
        return message
    return message[:157] + "..."


def _normalize_manolo_variants(manolo_msgs: Any) -> dict[str, str]:
    if isinstance(manolo_msgs, dict):
        variants = [manolo_msgs]
    elif isinstance(manolo_msgs, list):
        variants = [item for item in manolo_msgs if isinstance(item, dict)]
    else:
        variants = []

    normalized: dict[str, str] = {}
    for variant in variants:
        variant_type = str(variant.get("tipo") or variant.get("type") or "").strip()
        message = str(variant.get("mensaje") or variant.get("message") or "").strip()
        if variant_type and message:
            normalized[variant_type] = " ".join(message.split())
    return normalized


def _with_whatsapp_cta(message: str) -> str | None:
    clean = " ".join(str(message or "").split())
    clean_lower = clean.lower()
    if "613685560" in clean and ("whatsapp" in clean_lower or "wp" in clean_lower):
        return clean

    full_cta = " WhatsApp 613685560"
    if len(clean + full_cta) <= 160:
        return clean + full_cta

    short_cta = " Wp 613685560"
    if "613685560" not in clean and "whatsapp" not in clean_lower and len(clean + short_cta) <= 160:
        return clean + short_cta

    return None


def build_message(lead: dict[str, Any], tier: str) -> str:
    """Construye un SMS manteniendo un maximo de 160 caracteres."""
    variants = _normalize_manolo_variants(lead.get("manolo_msgs"))
    for variant_type in ("autoridad", "anti_venta"):
        message = variants.get(variant_type)
        if not message:
            continue

        with_cta = _with_whatsapp_cta(message)
        if with_cta and len(with_cta) <= 160:
            return with_cta

    return _fallback_message(lead, tier)


def _load_manolo_messages_by_lead_id() -> dict[str, Any]:
    messages: dict[str, Any] = {}
    for path in sorted(PATHS.runs.glob("*.json")):
        if path.name in {"enriched.json", "lead_status.json", "whatsapp_sent.json", "custom_searches.json"}:
            continue
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(run, dict):
            continue
        lead = run.get("lead") if isinstance(run.get("lead"), dict) else {}
        lead_id = str(run.get("lead_id") or lead.get("lead_id") or "").strip()
        manolo = run.get("manolo")
        if lead_id and manolo:
            messages[lead_id] = manolo
    return messages


def send_sms_dinahosting(phone: str, message: str, dry_run: bool = False) -> dict[str, Any]:
    """Envia un SMS via la API simple HTTP de Dinahosting."""
    if dry_run:
        return {"success": True, "dry_run": True, "phone": phone, "message": message}

    try:
        response = requests.post(
            DINAHOSTING_ENDPOINT,
            data={
                "AUTH_USER": DINAHOSTING_USER,
                "AUTH_PWD": DINAHOSTING_PASS,
                "command": "Sms_Send_Bulk_Limited_Gsm7",
                "account": DINAHOSTING_ACCOUNT,
                "contents": message,
                "to[]": phone,
                "from": "Mejoradora",
                "responseType": "Json",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        success = payload.get("responseCode") == 1000
        return {
            "success": success,
            "response_code": payload.get("responseCode"),
            "message_api": payload.get("message", ""),
            "phone": phone,
            "message": message,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "phone": phone,
            "message": message,
        }


def log_sms(result: dict[str, Any], lead_id: str, tier: str) -> None:
    """Guarda el resultado del intento en JSONL."""
    if result.get("dry_run"):
        return

    SMS_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lead_id": lead_id,
        "tier": tier,
        **result,
    }
    with SMS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_sent_phones() -> set[str]:
    """Carga telefonos marcados como enviados correctamente."""
    if not SMS_LOG.exists():
        return set()

    phones: set[str] = set()
    for line in SMS_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("success") and not entry.get("dry_run") and entry.get("phone"):
            phones.add(str(entry["phone"]))
    return phones


def load_leads(tier_filter: str | None = None) -> list[dict[str, Any]]:
    """Carga leads contactables desde ContactQueue construido sobre runs validos."""
    queue_items = build_contact_queue_from_runs(PATHS.runs)
    manolo_by_lead_id = _load_manolo_messages_by_lead_id()
    leads: list[dict[str, Any]] = []

    for item in queue_items:
        if item.tier not in {"A", "B"}:
            continue
        if tier_filter and item.tier != tier_filter:
            continue

        phone = normalize_phone(item.phone)
        if not phone:
            continue

        leads.append(
            {
                "lead_id": item.lead_id,
                "lead_name": item.business_name,
                "phone": phone,
                "tier": item.tier,
                "distance_km": item.distance_km,
                "contact_status": item.contact_status,
                "manolo_msgs": manolo_by_lead_id.get(item.lead_id, []),
            }
        )

    leads.sort(key=lambda lead: (lead["tier"], lead["lead_name"]))
    return leads


def validate_credentials() -> None:
    if all((DINAHOSTING_USER, DINAHOSTING_PASS, DINAHOSTING_ACCOUNT)):
        return
    print("ERROR: faltan DINAHOSTING_USER, DINAHOSTING_PASS o DINAHOSTING_ACCOUNT en el entorno.")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="SMS Engine Dinahosting")
    parser.add_argument("--tier", choices=["A", "B"], help="Filtrar por tier")
    parser.add_argument("--limit", type=int, default=MAX_SMS_PER_SESSION)
    parser.add_argument("--dry-run", action="store_true", help="Preview sin enviar")
    parser.add_argument("--cooldown", type=int, default=SMS_COOLDOWN_SECONDS)
    args = parser.parse_args()

    if not args.dry_run:
        validate_credentials()

    leads = load_leads(tier_filter=args.tier)
    sent_phones = load_sent_phones()
    new_leads = [lead for lead in leads if lead["phone"] not in sent_phones]

    print(f"{'[DRY RUN] ' if args.dry_run else ''}SMS Engine Dinahosting")
    print(f"  Total leads: {len(leads)} | Ya contactados: {len(sent_phones)} | Nuevos: {len(new_leads)}")
    print(f"  Limite: {args.limit} | Cooldown: {args.cooldown}s\n")

    sent = 0
    errors = 0
    previewed = 0

    for lead in new_leads[: args.limit]:
        message = build_message(lead, lead["tier"])
        print(f"  [{lead['tier']}] {lead['lead_name'][:30]:30} -> {lead['phone']} ({len(message)}ch)")
        if args.dry_run:
            print(f"      MSG: {message}")

        result = send_sms_dinahosting(lead["phone"], message, dry_run=args.dry_run)
        log_sms(result, lead["lead_id"], lead["tier"])

        if args.dry_run:
            previewed += 1
        elif result["success"]:
            sent += 1
        else:
            errors += 1
            print(f"      ERROR: {result.get('error', result.get('message_api', 'unknown'))}")

        if not args.dry_run and sent + errors < min(len(new_leads), args.limit):
            time.sleep(args.cooldown)

    if args.dry_run:
        print(f"\n  Preview: {previewed} | Errores simulados: {errors}")
    else:
        print(f"\n  Enviados: {sent} | Errores: {errors}")
        print(f"  Log: {SMS_LOG}")


if __name__ == "__main__":
    main()
