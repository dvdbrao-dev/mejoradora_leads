#!/usr/bin/env python3
"""Actualiza estado operativo propio de ContactQueue."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mejoradora_paths import get_project_paths
from mejoradora_statuses import (
    OFFICIAL_COMMERCIAL_STATUSES,
    OFFICIAL_CONTACT_STATUSES,
    OFFICIAL_REVIEW_STATUSES,
)


PATHS = get_project_paths(Path(__file__))
STATE_PATH = PATHS.runtime / "contact_queue_state.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state_map(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_state_map(path: Path, state_map: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _validate_choice(value: str | None, valid_values: set[str], flag: str) -> str | None:
    if value is None:
        return None
    if value not in valid_values:
        raise SystemExit(f"{flag} inválido: {value}. Valores válidos: {', '.join(sorted(valid_values))}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza estado operativo de ContactQueue por lead_id")
    parser.add_argument("lead_id", help="Lead_id exacto")
    parser.add_argument("--owner", help="Asignar owner")
    parser.add_argument("--review-status", help="Nuevo review_status")
    parser.add_argument("--contact-status", help="Nuevo contact_status")
    parser.add_argument("--commercial-status", help="Nuevo commercial_status")
    parser.add_argument("--last-contact-at", help="Timestamp ISO del último contacto")
    parser.add_argument("--mark-contacted-now", action="store_true", help="Guardar last_contact_at con timestamp UTC actual")
    parser.add_argument("--next-action", help="Siguiente acción manual")
    parser.add_argument("--notes", help="Notas operativas")
    args = parser.parse_args()

    review_status = _validate_choice(args.review_status, OFFICIAL_REVIEW_STATUSES, "--review-status")
    contact_status = _validate_choice(args.contact_status, OFFICIAL_CONTACT_STATUSES, "--contact-status")
    commercial_status = _validate_choice(args.commercial_status, OFFICIAL_COMMERCIAL_STATUSES, "--commercial-status")

    state_map = _load_state_map(STATE_PATH)
    lead_id = str(args.lead_id).strip()
    if not lead_id:
        raise SystemExit("lead_id vacío")

    current = dict(state_map.get(lead_id) or {})

    for field, value in (
        ("owner", args.owner),
        ("review_status", review_status),
        ("contact_status", contact_status),
        ("commercial_status", commercial_status),
        ("next_action", args.next_action),
        ("notes", args.notes),
    ):
        if value is not None:
            normalized = str(value).strip()
            if normalized:
                current[field] = normalized
            else:
                current.pop(field, None)

    if args.last_contact_at is not None:
        normalized = str(args.last_contact_at).strip()
        if normalized:
            current["last_contact_at"] = normalized
        else:
            current.pop("last_contact_at", None)

    if args.mark_contacted_now:
        current["last_contact_at"] = _utc_now_iso()

    current["updated_at"] = _utc_now_iso()
    state_map[lead_id] = current
    _save_state_map(STATE_PATH, state_map)

    print(json.dumps({"lead_id": lead_id, "state": current, "path": str(STATE_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
