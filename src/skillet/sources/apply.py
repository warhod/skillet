"""Re-materialize skills under `.skillet/skills/` from `sources.json` specs."""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path
from typing import Any

import httpx

from skillet.installer.copier import copy_skill
from skillet.sources.store import load_sources


def _download_http_zip(url: str, dest_dir: Path) -> None:
    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(dest_dir)
    except Exception as e:
        raise RuntimeError(f"Failed to download zip: {e}") from e


def _apply_one(
    skill_name: str,
    spec: dict[str, Any],
    project_dir: Path,
    skills_dest: Path,
) -> str | None:
    kind = spec.get("kind")
    if kind == "local":
        rel = str(spec.get("path", "")).strip()
        if not rel:
            return "local spec missing path"
        src = (project_dir / rel).resolve()
        if not src.exists():
            return f"local path does not exist: {rel}"
        if not src.is_dir() or not (src / "SKILL.md").exists():
            return f"not a skill directory (missing SKILL.md): {rel}"
        dest = skills_dest / skill_name
        if dest.exists():
            shutil.rmtree(dest)
        copy_skill(src, dest)
        return None
    if kind == "http_zip":
        url = str(spec.get("url", "")).strip()
        if not url:
            return "http_zip spec missing url"
        target = skills_dest / skill_name
        if target.exists():
            shutil.rmtree(target)
        try:
            _download_http_zip(url, skills_dest)
        except Exception as e:
            return str(e)
        return None
    if kind == "github":
        return "github sources are not supported yet (spec recorded only)"
    return f"unknown source kind: {kind!r}"


def apply_all_sources(project_dir: Path, skills_dest: Path) -> list[str]:
    """Apply every entry in `sources.json`. Returns human-readable errors (empty if all ok)."""
    skills_dest.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for name, spec in load_sources(project_dir).items():
        err = _apply_one(name, spec, project_dir, skills_dest)
        if err:
            errors.append(f"{name}: {err}")
    return errors
