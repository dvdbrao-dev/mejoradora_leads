#!/usr/bin/env python3
"""Envia mensajes de Manolo (variante anti_venta) por WhatsApp via HTTP local."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_paths import get_project_paths
from mejoradora_runtime import iter_valid_run_records, load_runtime_dict, load_runtime_list


PATHS = get_project_paths(Path(__file__))
RUNS_DIR = PATHS.runs
ENRICHED_PATH = RUNS_DIR / "enriched.json"
SENT_PATH = RUNS_DIR / "whatsapp_sent.json"
SEND_URL = "http://localhost:3001/send"
MAX_SENDS = 5
SLEEP_SECONDS = 5
TEST_MODE = True
TEST_PHONE = "34616785103"


def load_json(path: Path, default):
    if isinstance(default, dict):
        return load_runtime_dict(path)
    if isinstance(default, list):
        return load_runtime_list(path)
    return default


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:
        digits = f"34{digits}"
    return digits


def normalize_manolo_output(manolo_obj) -> list[dict]:
    if isinstance(manolo_obj, list):
        return [m for m in manolo_obj if isinstance(m, dict)]
    if isinstance(manolo_obj, dict):
        return [manolo_obj]
    return []


def build_latest_run_map() -> dict[str, dict]:
    latest_by_place_id: dict[str, tuple[float, dict]] = {}

    for path, run in iter_valid_run_records(RUNS_DIR):
        lead = run.get("lead", {})
        if not isinstance(lead, dict):
            continue
        place_id = lead.get("place_id")
        if not place_id or "manolo" not in run:
            continue

        mtime = path.stat().st_mtime
        prev = latest_by_place_id.get(place_id)
        if prev is None or mtime > prev[0]:
            latest_by_place_id[place_id] = (mtime, run)

    return {place_id: item[1] for place_id, item in latest_by_place_id.items()}


def extract_anti_venta_message(run: dict) -> str:
    variants = normalize_manolo_output(run.get("manolo"))
    for variant in variants:
        if str(variant.get("variant", "")).strip().lower() == "anti_venta":
            msg = str(variant.get("message", "")).strip()
            if msg:
                return msg
    return ""


def post_send(phone: str, message: str) -> dict:
    payload = json.dumps({"phone": phone, "message": message}).encode("utf-8")
    req = request.Request(
        SEND_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            parsed = json.loads(data) if data else {}
            return parsed if isinstance(parsed, dict) else {"ok": False, "error": "Respuesta inválida"}
    except error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {exc.code}: {body or exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    enriched = load_json(ENRICHED_PATH, {})
    if not isinstance(enriched, dict):
        print("0 mensajes enviados")
        return

    latest_runs = build_latest_run_map()
    previous_sent = load_json(SENT_PATH, [])
    if not isinstance(previous_sent, list):
        previous_sent = []

    sent_records: list[dict] = []
    sent_count = 0

    for place_id, lead_data in enriched.items():
        if sent_count >= MAX_SENDS:
            break
        if not isinstance(lead_data, dict):
            continue
        if str(lead_data.get("tier", "")).upper() != "A":
            continue

        raw_phone = lead_data.get("telefono", "")
        phone = normalize_phone(raw_phone)
        if not phone:
            continue

        run = latest_runs.get(place_id)
        if not run:
            continue

        message = extract_anti_venta_message(run)
        if not message:
            continue

        lead_name = lead_data.get("name") or run.get("lead_name") or place_id
        send_phone = TEST_PHONE if TEST_MODE else phone
        send_message = message
        if TEST_MODE:
            send_message = f"[TEST - Lead: {lead_name}] {message}"
            print(f"🧪 TEST_MODE activo: envío de prueba para {lead_name} -> {send_phone}")

        result = post_send(phone=send_phone, message=send_message)
        if result.get("ok") is True:
            sent_count += 1
            record = {
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "place_id": place_id,
                "lead_id": run.get("lead_id", ""),
                "lead_name": lead_name,
                "phone": phone,
                "send_phone": send_phone,
                "test_mode": TEST_MODE,
                "variant": "anti_venta",
                "message": send_message,
            }
            sent_records.append(record)
            print(f"✅ Enviado a {lead_name} ({send_phone})")
            if sent_count < MAX_SENDS:
                time.sleep(SLEEP_SECONDS)
        else:
            print(f"❌ Error enviando {place_id}: {result.get('error', 'desconocido')}")

    if sent_records:
        all_records = previous_sent + sent_records
        SENT_PATH.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{sent_count} mensajes enviados")


if __name__ == "__main__":
    main()
