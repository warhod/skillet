"""Add skills from local or GitHub specs (shared by CLI add flows)."""

from __future__ import annotations

import os
from pathlib import Path

from skillet.installer.lock import is_managed
from skillet.skills.parser import parse_skill_file
from skillet.sources import (
    MaterializeSummary,
    apply_all_sources,
    looks_like_local_source_spec,
    resolving,
    upsert_source,
)
from skillet.sources.github import (
    GitHubSourceSpec,
    parse_github_source_spec,
    serialize_github_source_spec,
)
from skillet.sources.store import load_sources


def _parse_local_add_spec(spec: str, project_dir: Path) -> tuple[str, dict] | None:
    raw = Path(spec).expanduser()
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw.resolve())
    else:
        candidates.append((project_dir / raw).resolve())
        candidates.append((Path.cwd() / raw).resolve())
    seen: set[Path] = set()
    for src in candidates:
        if src in seen:
            continue
        seen.add(src)
        if src.is_dir() and (src / "SKILL.md").exists():
            name = src.name
            try:
                rel = src.relative_to(project_dir).as_posix()
            except ValueError:
                rel = str(src)
            return name, {"kind": "local", "path": rel}
    return None


def _repo_root_for_dirs(dirs: list[Path]) -> Path:
    """Best-effort repository root for resolved skill directories."""
    resolved_paths = [d.resolve() for d in dirs]
    try:
        root = Path(os.path.commonpath([str(p) for p in resolved_paths]))
    except ValueError:
        return dirs[0].parent
    if len(dirs) == 1 and root.resolve() == dirs[0].resolve():
        return dirs[0].parent
    return root


def _github_skill_sources(
    *,
    dirs: list[Path],
    base: GitHubSourceSpec,
) -> list[tuple[str, dict[str, str]]]:
    """Map resolved github skill dirs to ``(name, source_spec)`` pairs."""
    repo_root = _repo_root_for_dirs(dirs)
    results: list[tuple[str, dict[str, str]]] = []
    for d in dirs:
        meta = parse_skill_file(d / "SKILL.md") or {}
        name = str(meta.get("name") or d.name).strip()
        if not name:
            continue
        rel = d.resolve().relative_to(repo_root.resolve()).as_posix()
        sub = rel if rel not in ("", ".") else None
        per = serialize_github_source_spec(
            GitHubSourceSpec(
                owner=base.owner,
                repo=base.repo,
                ref=base.ref,
                skill_subpath=sub,
            )
        )
        results.append((name, {"kind": "github", "spec": per}))
    return results


def add_specs(
    project_dir: Path,
    specs: list[str],
    *,
    skip_existing: bool = True,
    github_token: str | None = None,
) -> tuple[int, list[str]]:
    """
    For each spec, append entries to ``.skillet/config/sources.json`` (same semantics as ``skillet add``).

    Does **not** run ``apply_all_sources`` or native skill mirrors — call
    :func:`apply_sources_and_emit` afterward.
    """
    project_dir = project_dir.resolve()
    project_skills = project_dir / ".skillet" / "skills"
    project_skills.mkdir(parents=True, exist_ok=True)

    existing = load_sources(project_dir) if skip_existing else {}
    errors: list[str] = []
    tracked = 0

    def _unmanaged_collision(skill_name: str) -> bool:
        skill_file = project_skills / skill_name / "SKILL.md"
        return skill_file.exists() and not is_managed(project_dir, skill_name)

    for spec in specs:
        s = spec.strip()
        if not s:
            continue

        parsed = _parse_local_add_spec(s, project_dir)
        if parsed is not None:
            name, source_spec = parsed
            if _unmanaged_collision(name):
                errors.append(f"{name}: skill already exists (not managed by Skillet), skipping")
                continue
            if skip_existing and name in existing:
                continue
            upsert_source(project_dir, name, source_spec)
            tracked += 1
            existing[name] = source_spec
            continue

        if looks_like_local_source_spec(s):
            errors.append(f"{s}: local skill directory not found")
            continue

        try:
            base = parse_github_source_spec(s)
        except ValueError as e:
            errors.append(f"{s}: {e}")
            continue

        try:
            with resolving(s, cwd=project_dir, token=github_token) as resolved:
                dirs = resolved.skill_directories
        except Exception as e:
            errors.append(f"{s}: {e!s}")
            continue

        if not dirs:
            errors.append(f"{s}: no skills found")
            continue

        for name, source_spec in _github_skill_sources(dirs=dirs, base=base):
            if _unmanaged_collision(name):
                errors.append(f"{name}: skill already exists (not managed by Skillet), skipping")
                continue
            if skip_existing and name in existing:
                continue
            upsert_source(project_dir, name, source_spec)
            tracked += 1
            existing[name] = source_spec

    return tracked, errors


def apply_sources_and_emit(
    project_dir: Path,
    agent_flags: dict | None = None,
    *,
    github_token: str | None = None,
) -> tuple[list[str], dict[str, str], MaterializeSummary]:
    """Run ``apply_all_sources`` and refresh native agent skill directory mirrors."""
    from skillet.config.project import agent_emit_flags_for_project
    from skillet.installer.emitters import write_config_files

    project_dir = project_dir.resolve()
    project_skills = project_dir / ".skillet" / "skills"
    project_skills.mkdir(parents=True, exist_ok=True)
    errors, summary = apply_all_sources(project_dir, project_skills, github_token=github_token)
    flags = agent_flags if agent_flags is not None else agent_emit_flags_for_project(project_dir)
    written = write_config_files(project_skills, project_dir, flags)
    return errors, written, summary
