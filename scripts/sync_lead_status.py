#!/usr/bin/env python3
"""Sincroniza contact_status entre event log y frontmatter del vault.

Modo actual: event_log -> vault.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from event_log import EventLog


VAULT_DIR = Path.home() / "mejoradora-vault"
TARGET_DIRS = ("Leads/Tier-A", "Leads/Tier-B")


def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}

    frontmatter = text[4:end].splitlines()
    fields: dict[str, str] = {}
    for line in frontmatter:
        if not line or line.startswith("  - ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def update_frontmatter(path: Path, key: str, value: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False

    marker = "\n---\n"
    end = text.find(marker, 4)
    if end == -1:
        return False

    frontmatter = text[4:end]
    body = text[end + len(marker) :]
    lines = frontmatter.splitlines()
    updated = False

    for idx, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            new_line = f'{key}: "{value}"'
            if lines[idx] != new_line:
                lines[idx] = new_line
                updated = True
            break
    else:
        lines.append(f'{key}: "{value}"')
        updated = True

    if not updated:
        return False

    new_text = "---\n" + "\n".join(lines) + marker + body
    path.write_text(new_text, encoding="utf-8")
    return True


def note_paths() -> list[Path]:
    paths: list[Path] = []
    for rel_dir in TARGET_DIRS:
        directory = VAULT_DIR / rel_dir
        if directory.exists():
            paths.extend(sorted(directory.glob("*.md")))
    return paths


def main() -> None:
    log = EventLog()
    statuses = log.all_lead_statuses()

    updated = 0
    for note in note_paths():
        fm = read_frontmatter(note)
        lead_id = fm.get("lead_id")
        if not lead_id or lead_id not in statuses:
            continue

        current_status = statuses[lead_id]
        if fm.get("contact_status") == current_status:
            continue

        if update_frontmatter(note, "contact_status", current_status):
            print(f"  {note.name[:50]:50} -> {current_status}")
            updated += 1

    print(f"\n✅ {updated} notas actualizadas")


if __name__ == "__main__":
    main()
