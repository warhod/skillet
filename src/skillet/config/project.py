"""Per-project ``.skillet/config`` and resolved IDE flags for emitters."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from skillet.config.settings import IDE_KEYS, load_config, normalize_ide_support

PROJECT_CONFIG_VERSION = "1"


def get_project_config_dir(project_dir: Path) -> Path:
    return project_dir / ".skillet" / "config"


def project_config_path(project_dir: Path) -> Path:
    return get_project_config_dir(project_dir) / "config.json"


def load_project_config(project_dir: Path) -> dict:
    path = project_config_path(project_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_project_config(project_dir: Path, config: dict) -> None:
    get_project_config_dir(project_dir).mkdir(parents=True, exist_ok=True)
    project_config_path(project_dir).write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )


def ide_emit_flags_from_global() -> dict[str, bool]:
    """Emitter on/off map from global ``ide_support`` (fallback when project unset)."""
    config = load_config()
    default_ides = list(IDE_KEYS)
    keys = list(IDE_KEYS)
    raw = config.get("ide_support", default_ides)
    raw_norm = normalize_ide_support(raw if isinstance(raw, list) else [])
    if not raw_norm:
        raw_norm = default_ides
    flags = {k: k in raw_norm for k in keys}
    if not any(flags.values()):
        return {k: True for k in keys}
    return flags


def ide_emit_flags_for_project(project_dir: Path) -> dict[str, bool]:
    """Emitter on/off map: project ``ide_support`` overrides global defaults."""
    data = load_project_config(project_dir)
    raw = data.get("ide_support")
    keys = list(IDE_KEYS)
    if isinstance(raw, list) and raw:
        raw_norm = normalize_ide_support(raw)
        if raw_norm:
            flags = {k: k in raw_norm for k in keys}
            if any(flags.values()):
                return flags
    return ide_emit_flags_from_global()


def ensure_project_ide_support(project_dir: Path) -> None:
    """First-time project setup: prompt (TTY) or copy global defaults for ``ide_support``."""
    from skillet.config.settings import ide_multiselect_prompt_project
    from skillet.config.wizard import prompt_ide_targets

    valid = frozenset(IDE_KEYS)
    cfg = load_project_config(project_dir)
    existing = cfg.get("ide_support")
    if isinstance(existing, list) and existing:
        return

    g = load_config().get("ide_support", list(IDE_KEYS))
    if not isinstance(g, list) or not g:
        g = list(IDE_KEYS)

    if sys.stdin.isatty():
        chosen = prompt_ide_targets(
            message=ide_multiselect_prompt_project(),
            hint_previous_keys=[k for k in g if k in valid],
        )
    else:
        chosen = [k for k in g if k in valid] or list(IDE_KEYS)

    cfg.setdefault("version", PROJECT_CONFIG_VERSION)
    cfg["ide_support"] = chosen
    save_project_config(project_dir, cfg)
