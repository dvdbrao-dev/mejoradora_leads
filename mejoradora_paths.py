#!/usr/bin/env python3
"""Resolucion comun de paths para Mejoradora Leads."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ENV_VAR = "MEJORADORA_LEADS_HOME"
LEGACY_DIRNAME = "openfang"


def _looks_like_project_root(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "scripts").is_dir()
        and (path / "dashboard").is_dir()
        and (path / "data").exists()
        and (path / "schemas").is_dir()
    )


def _candidate_roots(anchor: Path | None = None) -> list[Path]:
    candidates: list[Path] = []

    env_home = os.getenv(ENV_VAR, "").strip()
    if env_home:
        candidates.append(Path(env_home).expanduser())

    if anchor is not None:
        start = anchor if anchor.is_dir() else anchor.parent
        candidates.extend([start, *start.parents])

    cwd = Path.cwd()
    candidates.extend([cwd, *cwd.parents])
    candidates.append(Path.home() / LEGACY_DIRNAME)
    return candidates


def resolve_project_home(anchor: Path | None = None) -> Path:
    seen: set[Path] = set()
    fallback: Path | None = None

    for candidate in _candidate_roots(anchor):
        resolved = candidate.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)

        if fallback is None and resolved.exists():
            fallback = resolved.resolve()

        if _looks_like_project_root(resolved):
            return resolved.resolve()

    if fallback is not None:
        return fallback

    if anchor is not None:
        resolved_anchor = anchor if anchor.is_dir() else anchor.parent
        return resolved_anchor.resolve()

    return Path.home() / LEGACY_DIRNAME


@dataclass(frozen=True)
class ProjectPaths:
    home: Path
    runs: Path
    runtime: Path
    outputs: Path
    inputs: Path
    inputs_raw: Path
    inputs_cleaned: Path
    data: Path
    schemas: Path
    dashboard: Path
    whatsapp: Path


def get_project_paths(anchor: Path | None = None) -> ProjectPaths:
    home = resolve_project_home(anchor)
    return ProjectPaths(
        home=home,
        runs=home / "runs",
        runtime=home / "runtime",
        outputs=home / "outputs",
        inputs=home / "inputs",
        inputs_raw=home / "inputs" / "raw",
        inputs_cleaned=home / "inputs" / "cleaned",
        data=home / "data",
        schemas=home / "schemas",
        dashboard=home / "dashboard",
        whatsapp=home / "whatsapp",
    )
