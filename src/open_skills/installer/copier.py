import shutil
from pathlib import Path


def copy_skill(src: Path, dest: Path) -> None:
    """Copy a skill directory to the destination."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def copy_all_skills(skills_src: Path, skills_dest: Path) -> int:
    """Copy all skills from source to destination. Returns count of copied skills."""
    skills_dest.mkdir(parents=True, exist_ok=True)

    count = 0
    for entry in skills_src.iterdir():
        if entry.is_dir() and (entry / 'SKILL.md').exists():
            copy_skill(entry, skills_dest / entry.name)
            count += 1

    return count


def remove_skill(skills_dir: Path, skill_name: str) -> bool:
    """Remove a skill by name. Returns True if removed."""
    skill_path = skills_dir / skill_name
    if skill_path.exists():
        shutil.rmtree(skill_path)
        return True
    return False