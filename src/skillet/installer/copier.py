import shutil
from pathlib import Path

from skillet.installer.lock import is_managed, load_lock, record_skill


def _existing_mirrors(project_dir: Path, skill_name: str) -> list[str]:
    entry = load_lock(project_dir).get("skills", {}).get(skill_name, {})
    mirrors = entry.get("mirrors") if isinstance(entry, dict) else []
    if not isinstance(mirrors, list):
        return []
    return [m for m in mirrors if isinstance(m, str) and m.strip()]


def copy_skill(src: Path, dest: Path, *, project_dir: Path | None = None) -> bool:
    """Copy a skill directory to the destination."""
    skill_name = dest.name
    if dest.exists():
        if project_dir is not None and not is_managed(project_dir, skill_name):
            return False
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return True


def copy_all_skills(skills_src: Path, skills_dest: Path) -> int:
    """Copy all skills from source to destination. Returns count of copied skills."""
    project_dir = skills_dest.parent.parent
    skills_dest.mkdir(parents=True, exist_ok=True)

    count = 0
    for entry in skills_src.iterdir():
        if entry.is_dir() and (entry / 'SKILL.md').exists():
            dest = skills_dest / entry.name
            copied = copy_skill(entry, dest, project_dir=project_dir)
            if not copied:
                print(f"  ~ {entry.name} already present (not managed by Skillet), skipping")
                continue
            record_skill(
                project_dir,
                entry.name,
                origin="bundled",
                mirrors=_existing_mirrors(project_dir, entry.name),
            )
            count += 1

    return count


def remove_skill(skills_dir: Path, skill_name: str) -> bool:
    """Remove a skill by name. Returns True if removed."""
    skill_path = skills_dir / skill_name
    if skill_path.exists():
        shutil.rmtree(skill_path)
        return True
    return False