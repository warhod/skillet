"""Project-local `.skillet/config/sources.json`: installed skill name -> source spec."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def sources_json_path(project_dir: Path) -> Path:
    return project_dir / ".skillet" / "config" / "sources.json"


def _legacy_sources_json_path(project_dir: Path) -> Path:
    return project_dir / ".skillet" / "sources.json"


def _normalize_sources(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if isinstance(value, dict) and value.get("kind"):
            out[key] = dict(value)
    return out


def load_sources(project_dir: Path) -> dict[str, dict[str, Any]]:
    path = sources_json_path(project_dir)
    if not path.exists():
        legacy = _legacy_sources_json_path(project_dir)
        if legacy.exists():
            try:
                data = json.loads(legacy.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
            if isinstance(data, dict):
                normalized = _normalize_sources(data)
                if normalized:
                    save_sources(project_dir, normalized)
                    legacy.unlink(missing_ok=True)
                    return normalized
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return _normalize_sources(data)


def save_sources(project_dir: Path, sources: dict[str, dict[str, Any]]) -> None:
    path = sources_json_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(sources.items()))
    path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
    _legacy_sources_json_path(project_dir).unlink(missing_ok=True)


def upsert_source(project_dir: Path, skill_name: str, spec: dict[str, Any]) -> None:
    sources = load_sources(project_dir)
    sources[skill_name] = dict(spec)
    save_sources(project_dir, sources)


def remove_source_entry(project_dir: Path, skill_name: str) -> bool:
    sources = load_sources(project_dir)
    if skill_name not in sources:
        return False
    del sources[skill_name]
    if sources:
        save_sources(project_dir, sources)
    else:
        path = sources_json_path(project_dir)
        if path.exists():
            path.unlink()
    return True
