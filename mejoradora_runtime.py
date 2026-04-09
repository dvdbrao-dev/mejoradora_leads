#!/usr/bin/env python3
"""Helpers para runtime local y lectura robusta de runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


AUXILIARY_RUNTIME_FILES = {
    "custom_searches.json",
    "enriched.json",
    "lead_status.json",
    "whatsapp_sent.json",
}


def load_json_file(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def is_auxiliary_runtime_file(path: Path) -> bool:
    return path.name in AUXILIARY_RUNTIME_FILES


def is_valid_run_record(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False

    lead = payload.get("lead")
    if not isinstance(lead, dict):
        return False

    if not (payload.get("lead_id") or lead.get("lead_id") or payload.get("lead_name") or lead.get("lead_name")):
        return False

    return any(
        key in payload
        for key in ("status", "started_at", "finished_at", "paco", "esther", "manolo", "auditor")
    )


def iter_valid_run_records(runs_dir: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    if not runs_dir.exists():
        return

    for path in sorted(runs_dir.glob("*.json")):
        if is_auxiliary_runtime_file(path):
            continue

        payload = load_json_file(path)
        if not is_valid_run_record(payload):
            continue

        yield path, payload


def load_runtime_dict(path: Path) -> dict[str, Any]:
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else {}


def load_runtime_list(path: Path) -> list[Any]:
    payload = load_json_file(path)
    return payload if isinstance(payload, list) else []
