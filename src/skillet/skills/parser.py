import html
import re
from collections.abc import Callable
from pathlib import Path

import ruamel.yaml


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from SKILL.md content."""
    match = re.match(r'^---\n([\s\S]*?)\n---', content)
    if not match:
        return {}

    yaml = ruamel.yaml.YAML(typ='safe')
    try:
        return yaml.load(match.group(1)) or {}
    except Exception:
        return {}


def parse_skill_file(skill_path: Path) -> dict | None:
    """Parse a SKILL.md file and extract metadata."""
    if not skill_path.exists():
        return None

    content = skill_path.read_text(encoding='utf-8')
    frontmatter = parse_frontmatter(content)

    return {
        'name': frontmatter.get('name', skill_path.parent.name),
        'description': frontmatter.get('description', ''),
        'path': str(skill_path),
        'skill_file': str(skill_path),
    }


def get_skills_from_directory(skills_dir: Path) -> list[dict]:
    """Scan a directory for skills (directories with SKILL.md)."""
    if not skills_dir.exists():
        return []

    skills = []
    for entry in skills_dir.iterdir():
        if not entry.is_dir():
            continue

        skill_file = entry / 'SKILL.md'
        if skill_file.exists():
            skill = parse_skill_file(skill_file)
            if skill:
                skills.append(skill)

    return sorted(skills, key=lambda s: s['name'])


def generate_skills_xml(
    skills: list[dict],
    base_dir: Path,
    *,
    rel_location: Callable[[dict], str] | None = None,
) -> str:
    """Generate <available_skills> XML block for system prompts.

    If ``rel_location`` is set, it returns the path string stored in each
    ``<location>`` entry (typically repo-relative). Otherwise paths are derived
    from ``skill['skill_file']`` relative to ``base_dir``.
    """
    xml = '<available_skills>\n'

    for skill in skills:
        if rel_location is not None:
            rel_path = rel_location(skill)
        else:
            rel_path = str(Path(skill['skill_file']).relative_to(base_dir))
        xml += '  <skill>\n'
        xml += f'    <name>{html.escape(str(skill["name"]), quote=False)}</name>\n'
        xml += f'    <description>{html.escape(str(skill["description"]), quote=False)}</description>\n'
        xml += f'    <location>{html.escape(rel_path, quote=False)}</location>\n'
        xml += '  </skill>\n'

    xml += '</available_skills>'
    return xml