#!/usr/bin/env python3
"""Event log append-only para tracking comercial de leads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


TERMINAL = {"closed_won", "closed_lost", "no_response"}
FUNNEL_ORDER = [
    "pending",
    "sms_sent",
    "sms_failed",
    "whatsapp_received",
    "call_scheduled",
    "call_done",
    "visit_scheduled",
    "visit_done",
    "study_sent",
    "proposal_sent",
    "closed_won",
    "closed_lost",
    "no_response",
]
FUNNEL_INDEX = {status: idx for idx, status in enumerate(FUNNEL_ORDER)}


class EventLog:
    def __init__(self, path: Path | str = "data/logs/lead_events.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, lead_id: str, event_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lead_id": lead_id,
            "event_type": event_type,
            "data": data or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def all_events(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def for_lead(self, lead_id: str) -> list[dict[str, Any]]:
        return [event for event in self.all_events() or [] if event.get("lead_id") == lead_id]

    def current_status(self, lead_id: str) -> str:
        events = self.for_lead(lead_id)
        if not events:
            return "pending"
        current = "pending"
        for event in events:
            event_type = str(event.get("event_type") or "").strip()
            if not event_type:
                continue
            if current in TERMINAL:
                continue
            current = event_type
        return current

    def all_lead_statuses(self) -> dict[str, str]:
        statuses: dict[str, str] = {}
        for event in self.all_events() or []:
            lead_id = str(event.get("lead_id") or "").strip()
            event_type = str(event.get("event_type") or "").strip()
            if not lead_id:
                continue
            current = statuses.get(lead_id, "pending")
            if current in TERMINAL:
                continue
            if event_type:
                statuses[lead_id] = event_type
        return statuses


if __name__ == "__main__":
    log = EventLog()
    events = list(log.all_events() or [])
    print(f"Total eventos: {len(events)}")
    statuses = log.all_lead_statuses()
    print(f"Leads con eventos: {len(statuses)}")
    for lead_id, status in list(statuses.items())[:5]:
        print(f"  {lead_id}: {status}")
