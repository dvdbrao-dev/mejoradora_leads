#!/usr/bin/env python3
"""Migra sms_sent.jsonl al event log unificado sin duplicar eventos."""

from __future__ import annotations

import json
from pathlib import Path

from event_log import EventLog


SMS_LOG = Path("data/logs/sms_sent.jsonl")


def build_event_from_sms(sms: dict) -> dict:
    event_type = "sms_sent" if sms.get("success") else "sms_failed"
    return {
        "lead_id": sms["lead_id"],
        "event_type": event_type,
        "data": {
            "tier": sms.get("tier"),
            "phone": sms.get("phone"),
            "message": sms.get("message"),
            "error": sms.get("error"),
            "response_code": sms.get("response_code"),
            "message_api": sms.get("message_api"),
            "timestamp_original": sms.get("timestamp"),
            "source": "sms_sent.jsonl",
        },
    }


def main() -> None:
    if not SMS_LOG.exists():
        print("No hay sms_sent.jsonl")
        return

    log = EventLog()
    existing_keys = {
        (
            str(event.get("lead_id") or ""),
            str(event.get("event_type") or ""),
            str((event.get("data") or {}).get("timestamp_original") or ""),
        )
        for event in (log.all_events() or [])
    }

    migrated = 0
    skipped = 0
    with SMS_LOG.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            sms = json.loads(line)
            event = build_event_from_sms(sms)
            dedupe_key = (
                event["lead_id"],
                event["event_type"],
                str(event["data"].get("timestamp_original") or ""),
            )
            if dedupe_key in existing_keys:
                skipped += 1
                continue
            log.record(
                lead_id=event["lead_id"],
                event_type=event["event_type"],
                data=event["data"],
            )
            existing_keys.add(dedupe_key)
            migrated += 1

    print(f"✅ Migrados {migrated} eventos SMS a lead_events.jsonl")
    if skipped:
        print(f"ℹ️ Omitidos por duplicado: {skipped}")


if __name__ == "__main__":
    main()
