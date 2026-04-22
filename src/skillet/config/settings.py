"""Shared IDE metadata and global user config (~/.config/skillet/config.json)."""

from __future__ import annotations

import json
from pathlib import Path

IDE_KEYS = ("claude", "cursor", "gemini")
IDE_LABELS: dict[str, str] = {
    "claude": "Claude Code",
    "cursor": "Cursor",
    "gemini": "Gemini CLI",
}


def normalize_ide_support(keys: list[str] | None) -> list[str]:
    """Drop unknown keys from stored lists."""
    if not isinstance(keys, list):
        return []
    return [k for k in keys if k in IDE_KEYS]


def ide_checkbox_instruction() -> str:
    return "(Space = select, Enter = confirm; at least one required)"


def ide_multiselect_usage_line() -> str:
    return (
        "Nothing is pre-selected — press Space on each IDE you use, then Enter."
    )


def ide_multiselect_prompt_global() -> str:
    return f"Which IDEs do you use?\n  {ide_multiselect_usage_line()}"


def ide_multiselect_prompt_project() -> str:
    return (
        "Which IDEs should this project target?\n"
        f"  {ide_multiselect_usage_line()}"
    )


def ide_reference_hint_line(keys: list[str]) -> str | None:
    labels = [IDE_LABELS[k] for k in keys if k in IDE_LABELS]
    if not labels:
        return None
    return (
        f"  (For reference: {', '.join(labels)} — use Space to select what applies.)"
    )


def get_config_path() -> Path:
    config_dir = Path.home() / ".config" / "skillet"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def _lean_config_from_raw(raw: dict | None) -> dict:
    """Only fields Skillet reads; strips legacy keys from older installs."""
    if not isinstance(raw, dict):
        raw = {}
    ide = normalize_ide_support(raw.get("ide_support"))
    if not ide:
        ide = list(IDE_KEYS)
    token = raw.get("github_token")
    gh = token.strip() if isinstance(token, str) else ""
    return {"ide_support": ide, "github_token": gh}


def load_config() -> dict:
    path = get_config_path()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}
        return _lean_config_from_raw(raw)
    return _lean_config_from_raw({})


def save_config(config: dict) -> None:
    payload = _lean_config_from_raw(config)
    get_config_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
