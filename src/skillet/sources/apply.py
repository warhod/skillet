"""Re-materialize skills under `.skillet/skills/` from `.skillet/config/sources.json` specs."""

from __future__ import annotations

import importlib
import io
import shutil
import zipfile
from pathlib import Path
from typing import Any

import httpx

from skillet.installer.copier import copy_skill
from skillet.skills.parser import parse_skill_file
from skillet.sources.store import load_sources


def _pick_github_skill_dir(dirs: list[Path], skill_name: str) -> Path | None:
    if len(dirs) == 1:
        return dirs[0]
    by_dir = [d for d in dirs if d.name == skill_name]
    if len(by_dir) == 1:
        return by_dir[0]
    by_meta: list[Path] = []
    for d in dirs:
        meta = parse_skill_file(d / "SKILL.md")
        if meta and str(meta.get("name", "")).strip() == skill_name:
            by_meta.append(d)
    if len(by_meta) == 1:
        return by_meta[0]
    return None


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
    *,
    github_token: str | None,
) -> str | None:
    kind = spec.get("kind")
    if kind == "local":
        rel = str(spec.get("path", "")).strip()
        local_source = str(spec.get("source", "")).strip()
        if not rel and local_source:
            rel = (Path("skills") / local_source).as_posix()
        if not rel:
            return "local spec missing path/source"
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
        spec_str = str(spec.get("spec", "") or spec.get("github", "")).strip()
        if not spec_str:
            return "github spec missing spec"
        sources_mod = importlib.import_module("skillet.sources")
        resolving = sources_mod.resolving
        try:
            with resolving(spec_str, cwd=project_dir, token=github_token) as r:
                dirs = list(r.skill_directories)
                if not dirs:
                    return "no SKILL.md directories found in github archive"
                chosen = _pick_github_skill_dir(dirs, skill_name)
                if chosen is None:
                    return (
                        "ambiguous github source (multiple skills); use owner/repo/path "
                        f"or match directory / frontmatter name to '{skill_name}'"
                    )
                dest = skills_dest / skill_name
                if dest.exists():
                    shutil.rmtree(dest)
                # Copy before leaving the context; temp extraction is cleaned on exit.
                copy_skill(chosen, dest)
        except Exception as e:
            return str(e)
        return None
    return f"unknown source kind: {kind!r}"


def apply_all_sources(
    project_dir: Path,
    skills_dest: Path,
    *,
    github_token: str | None = None,
) -> list[str]:
    """Apply every entry in ``.skillet/config/sources.json``."""
    skills_dest.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for name, spec in load_sources(project_dir).items():
        err = _apply_one(
            name, spec, project_dir, skills_dest, github_token=github_token
        )
        if err:
            errors.append(f"{name}: {err}")
    return errors
