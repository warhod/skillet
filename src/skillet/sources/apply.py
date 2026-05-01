"""Re-materialize skills under `.skillet/skills/` from ``sources.json`` and prune removed entries."""

from __future__ import annotations

from dataclasses import dataclass
import io
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

import httpx

from skillet.installer.copier import copy_skill
from skillet.installer.lock import existing_mirrors, is_managed, record_skill
from skillet.skills.parser import parse_skill_file
from skillet.sources.github import fetch_github_skill_directories, parse_github_source_spec
from skillet.sources.store import load_sources


@dataclass(frozen=True)
class MaterializeSummary:
    """Changes under ``.skillet/skills/`` after applying ``sources.json``."""

    added: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: tuple[str, ...]


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
            dest_dir_resolved = dest_dir.resolve()
            for member in zf.infolist():
                member_path = (dest_dir_resolved / member.filename).resolve()
                if not member_path.is_relative_to(dest_dir_resolved):
                    raise RuntimeError(f"Zip slip vulnerability detected: {member.filename}")
                zf.extract(member, dest_dir)
    except Exception as e:
        raise RuntimeError(f"Failed to download zip: {e}") from e


def _apply_local_spec(
    project_dir: Path,
    skills_dest: Path,
    skill_name: str,
    spec: dict[str, Any],
    mirrors: list[str],
) -> str | None:
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
    copy_skill(src, skills_dest / skill_name)
    record_skill(project_dir, skill_name, origin=f"local:{rel}", mirrors=mirrors)
    return None


def _apply_http_zip_spec(
    project_dir: Path,
    skills_dest: Path,
    skill_name: str,
    spec: dict[str, Any],
    mirrors: list[str],
) -> str | None:
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
    record_skill(project_dir, skill_name, origin=f"http_zip:{url}", mirrors=mirrors)
    return None


def _apply_github_spec(
    project_dir: Path,
    skills_dest: Path,
    skill_name: str,
    spec: dict[str, Any],
    mirrors: list[str],
    *,
    github_token: str | None,
) -> str | None:
    spec_str = str(spec.get("spec", "") or spec.get("github", "")).strip()
    if not spec_str:
        return "github spec missing spec"
    try:
        parsed_spec = parse_github_source_spec(spec_str)
        dirs, cleanup = fetch_github_skill_directories(parsed_spec, token=github_token)
    except Exception as e:
        return str(e)
    try:
        if not dirs:
            return "no SKILL.md directories found in github archive"
        chosen = _pick_github_skill_dir(dirs, skill_name)
        if chosen is None:
            return (
                "ambiguous github source (multiple skills); use owner/repo/path "
                f"or match directory / frontmatter name to '{skill_name}'"
            )
        # Copy before cleanup; temp extraction is removed in finally.
        copy_skill(chosen, skills_dest / skill_name)
    except Exception as e:
        return str(e)
    finally:
        cleanup()
    record_skill(project_dir, skill_name, origin=f"github:{spec_str}", mirrors=mirrors)
    return None


def _apply_one(
    skill_name: str,
    spec: dict[str, Any],
    project_dir: Path,
    skills_dest: Path,
    *,
    github_token: str | None,
) -> str | None:
    dest = skills_dest / skill_name
    if dest.exists() and not is_managed(project_dir, skill_name):
        return "skill already exists (not managed by Skillet), skipping"

    mirrors = existing_mirrors(project_dir, skill_name)

    kind = spec.get("kind")
    if kind == "local":
        return _apply_local_spec(project_dir, skills_dest, skill_name, spec, mirrors)
    if kind == "http_zip":
        return _apply_http_zip_spec(project_dir, skills_dest, skill_name, spec, mirrors)
    if kind == "github":
        return _apply_github_spec(
            project_dir,
            skills_dest,
            skill_name,
            spec,
            mirrors,
            github_token=github_token,
        )
    return f"unknown source kind: {kind!r}"


def _prune_untracked_skills(skills_dest: Path, tracked: set[str]) -> list[str]:
    """Remove materialized skill dirs not listed in ``sources.json``; return removed names."""
    removed: list[str] = []
    if not skills_dest.is_dir():
        return removed
    for entry in list(skills_dest.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name in tracked:
            continue
        removed.append(entry.name)
        shutil.rmtree(entry)
    return sorted(removed)


def apply_all_sources(
    project_dir: Path,
    skills_dest: Path,
    *,
    github_token: str | None = None,
) -> tuple[list[str], MaterializeSummary]:
    """Apply every entry in ``.skillet/config/sources.json`` and drop untracked skill dirs."""
    skills_dest.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    sources = load_sources(project_dir)
    existing_before = {p.name for p in skills_dest.iterdir() if p.is_dir()}
    added_names: list[str] = []
    unchanged_names: list[str] = []
    for name, spec in sources.items():
        existed = name in existing_before
        err = _apply_one(
            name, spec, project_dir, skills_dest, github_token=github_token
        )
        if err:
            errors.append(f"{name}: {err}")
        elif existed:
            unchanged_names.append(name)
        else:
            added_names.append(name)
    removed_names = _prune_untracked_skills(skills_dest, set(sources.keys()))
    summary = MaterializeSummary(
        added=tuple(sorted(added_names)),
        removed=tuple(removed_names),
        unchanged=tuple(sorted(unchanged_names)),
    )
    return errors, summary
