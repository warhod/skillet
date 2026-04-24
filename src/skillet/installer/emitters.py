"""Emit mirrored native skill directories (see ``AGENT_NATIVE_SKILL_REL_PATH``)."""

from __future__ import annotations

import shutil
from pathlib import Path

from skillet.config.settings import AGENT_KEYS, AGENT_NATIVE_SKILL_REL_PATH
from skillet.installer.lock import load_lock, save_lock

_LEGACY_TO_REMOVE: tuple[Path, ...] = (
    # Removed in native-only Skillet: migrate away from these paths.
    Path(".cursor/rules/skillet.mdc"),
    Path(".github/copilot-instructions.md"),
)


def _remove_legacy_rule_and_index_files(project_dir: Path) -> None:
    """Delete rule/index files from older Skillet versions if present."""
    for rel in _LEGACY_TO_REMOVE:
        p = project_dir / rel
        if p.is_file():
            p.unlink()
        # Remove empty parent dirs for rules only (e.g. .github if empty)
        if rel.as_posix() == ".github/copilot-instructions.md":
            gh = project_dir / ".github"
            if gh.is_dir() and not any(gh.iterdir()):
                gh.rmdir()


def _native_rel_paths_needed(config: dict) -> set[str]:
    """Relative mirror roots (posix) that should exist for enabled agents."""
    needed: set[str] = set()
    for k in AGENT_KEYS:
        if not config.get(k):
            continue
        rel = AGENT_NATIVE_SKILL_REL_PATH.get(k)
        if rel:
            needed.add(rel)
    return needed


def _prune_disabled_emitters(project_dir: Path, config: dict) -> None:
    """Remove mirrored skill trees when no enabled agent uses that root."""
    needed = _native_rel_paths_needed(config)
    lock = load_lock(project_dir)
    skills = lock.get("skills", {})
    for rel in {p for p in AGENT_NATIVE_SKILL_REL_PATH.values() if p}:
        if rel in needed:
            continue
        tree = project_dir / rel
        if not tree.is_dir():
            continue
        for entry in tree.iterdir():
            if not entry.is_dir():
                continue
            rel_skill_md = (entry / "SKILL.md").relative_to(project_dir).as_posix()
            owned = False
            for lock_entry in skills.values():
                if not isinstance(lock_entry, dict):
                    continue
                mirrors = lock_entry.get("mirrors")
                if not isinstance(mirrors, list):
                    continue
                if rel_skill_md in mirrors:
                    owned = True
                    lock_entry["mirrors"] = [m for m in mirrors if m != rel_skill_md]
                    break
            if owned:
                shutil.rmtree(entry)
        if tree.is_dir() and not any(tree.iterdir()):
            tree.rmdir()
    save_lock(project_dir, lock)


def emit_native_skills(skills_dir: Path, dest_root: Path, project_dir: Path | None = None) -> None:
    """Mirror each skill at ``<dest_root>/<name>/SKILL.md`` and prune removed skills.

    ``dest_root`` is a value from ``AGENT_NATIVE_SKILL_REL_PATH`` (e.g. ``.claude/skills``).
    """
    dest_root.mkdir(parents=True, exist_ok=True)

    valid_names: set[str] = set()
    if skills_dir.exists():
        for entry in skills_dir.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").exists():
                valid_names.add(entry.name)

    managed_mirror_dirs: set[str] = set()
    lock: dict | None = None
    if project_dir is not None:
        lock = load_lock(project_dir)
        for entry in lock.get("skills", {}).values():
            if not isinstance(entry, dict):
                continue
            mirrors = entry.get("mirrors")
            if not isinstance(mirrors, list):
                continue
            for mirror in mirrors:
                if not isinstance(mirror, str) or not mirror.strip():
                    continue
                p = project_dir / mirror
                if p.parent == dest_root:
                    managed_mirror_dirs.add(p.parent.relative_to(project_dir).as_posix())

    for child in dest_root.iterdir():
        if not child.is_dir() or child.name in valid_names:
            continue
        if project_dir is None:
            shutil.rmtree(child)
            continue
        rel_child = child.relative_to(project_dir).as_posix()
        if rel_child in managed_mirror_dirs:
            rel_skill_md = (child / "SKILL.md").relative_to(project_dir).as_posix()
            for entry in lock.get("skills", {}).values():
                if not isinstance(entry, dict):
                    continue
                mirrors = entry.get("mirrors")
                if not isinstance(mirrors, list):
                    continue
                entry["mirrors"] = [m for m in mirrors if m != rel_skill_md]
            shutil.rmtree(child)

    for name in sorted(valid_names, key=str.lower):
        src = skills_dir / name / "SKILL.md"
        target_dir = dest_root / name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "SKILL.md"
        shutil.copy2(src, target_file)

        if lock is not None and project_dir is not None:
            skills = lock.setdefault("skills", {})
            entry = skills.setdefault(name, {"origin": "", "mirrors": []})
            mirrors = entry.get("mirrors")
            if not isinstance(mirrors, list):
                mirrors = []
            rel_target = target_file.relative_to(project_dir).as_posix()
            entry["mirrors"] = sorted(
                {m for m in mirrors if isinstance(m, str) and m.strip()} | {rel_target}
            )

    if lock is not None and project_dir is not None:
        save_lock(project_dir, lock)


def emit_claude_code_skills(skills_dir: Path, project_dir: Path) -> None:
    """Mirror each skill under ``.claude/skills/<name>/`` for Claude Code discovery."""
    emit_native_skills(skills_dir, project_dir / ".claude" / "skills", project_dir)


def write_config_files(skills_dir: Path, project_dir: Path, config: dict) -> dict:
    """Write native skill directory trees for enabled agent targets. Returns paths written."""
    _remove_legacy_rule_and_index_files(project_dir)
    _prune_disabled_emitters(project_dir, config)
    result: dict[str, str] = {}
    seen: set[Path] = set()

    for k in AGENT_KEYS:
        if not config.get(k):
            continue
        rel = AGENT_NATIVE_SKILL_REL_PATH.get(k)
        if not rel:
            continue
        root = project_dir / rel
        if root in seen:
            continue
        seen.add(root)
        emit_native_skills(skills_dir, root, project_dir)
        key = rel if rel.endswith("/") else f"{rel}/"
        result[key] = str(root)

    return result
