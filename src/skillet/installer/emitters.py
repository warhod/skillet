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


def _iter_lock_skill_entries(lock: dict) -> list[dict]:
    """Return mutable lock skill entries that are dictionaries."""
    skills = lock.get("skills", {})
    if not isinstance(skills, dict):
        return []
    return [entry for entry in skills.values() if isinstance(entry, dict)]


def _remove_mirror_from_lock_entries(entries: list[dict], rel_skill_md: str) -> bool:
    """Drop one mirror path from lock entries; return True if it was removed."""
    for entry in entries:
        mirrors = entry.get("mirrors")
        if not isinstance(mirrors, list):
            continue
        if rel_skill_md not in mirrors:
            continue
        entry["mirrors"] = [m for m in mirrors if m != rel_skill_md]
        return True
    return False


def _tracked_mirror_dirs(entries: list[dict], dest_root: Path, project_dir: Path) -> set[str]:
    """Return mirror directory paths under dest_root tracked in lock."""
    tracked: set[str] = set()
    for entry in entries:
        mirrors = entry.get("mirrors")
        if not isinstance(mirrors, list):
            continue
        for mirror in mirrors:
            if not isinstance(mirror, str) or not mirror.strip():
                continue
            mirror_path = Path(mirror)
            # Lock mirrors may be either ".../<skill>/SKILL.md" or ".../<skill>".
            skill_dir_rel = (
                mirror_path.parent if mirror_path.name == "SKILL.md" else mirror_path
            )
            skill_dir_abs = project_dir / skill_dir_rel
            if skill_dir_abs.parent == dest_root:
                tracked.add(skill_dir_rel.as_posix())
    return tracked


def _remove_legacy_rule_and_index_files(project_dir: Path) -> None:
    """Delete rule/index files from older Skillet versions if present."""
    for rel in _LEGACY_TO_REMOVE:
        p = project_dir / rel
        if p.is_file():
            p.unlink()
        parent = p.parent
        if parent != project_dir and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()


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
    lock_entries = _iter_lock_skill_entries(lock)
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
            if _remove_mirror_from_lock_entries(lock_entries, rel_skill_md):
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
    lock_entries: list[dict] = []
    if project_dir is not None:
        lock = load_lock(project_dir)
        lock_entries = _iter_lock_skill_entries(lock)
        managed_mirror_dirs = _tracked_mirror_dirs(lock_entries, dest_root, project_dir)

    for child in dest_root.iterdir():
        if not child.is_dir() or child.name in valid_names:
            continue
        # ``unrecord_skill`` may have removed only SKILL.md, leaving an empty dir behind.
        if not any(child.iterdir()):
            shutil.rmtree(child)
            continue
        if project_dir is None:
            shutil.rmtree(child)
            continue
        rel_child = child.relative_to(project_dir).as_posix()
        if rel_child in managed_mirror_dirs:
            rel_skill_md = (child / "SKILL.md").relative_to(project_dir).as_posix()
            _remove_mirror_from_lock_entries(lock_entries, rel_skill_md)
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
