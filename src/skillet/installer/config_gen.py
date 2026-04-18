import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from skillet.skills.parser import get_skills_from_directory, generate_skills_xml


def get_templates_dir() -> Path:
    return Path(__file__).parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(get_templates_dir())),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _remove_legacy_ide_files(project_dir: Path) -> None:
    legacy = project_dir / ".cursorrules"
    if legacy.is_file():
        legacy.unlink()
    copilot = project_dir / ".github" / "copilot-instructions.md"
    if copilot.is_file():
        copilot.unlink()
    for legacy_rules in (
        project_dir / ".cursor" / "rules" / "openskills.mdc",
        project_dir / ".cursor" / "rules" / "open-skills.mdc",
    ):
        if legacy_rules.is_file():
            legacy_rules.unlink()


def emit_claude_code_skills(skills_dir: Path, project_dir: Path) -> None:
    """Copy each skill into ``.claude/skills/<name>/`` for Claude Code discovery."""
    dest_root = project_dir / ".claude" / "skills"
    dest_root.mkdir(parents=True, exist_ok=True)

    valid_names: set[str] = set()
    if skills_dir.exists():
        for entry in skills_dir.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").exists():
                valid_names.add(entry.name)

    for child in dest_root.iterdir():
        if child.is_dir() and child.name not in valid_names:
            shutil.rmtree(child)

    for name in sorted(valid_names, key=str.lower):
        src = skills_dir / name / "SKILL.md"
        target_dir = dest_root / name
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target_dir / "SKILL.md")


def generate_claude_md(skills: list[dict], project_dir: Path) -> str:
    skills_xml = generate_skills_xml(
        skills,
        project_dir,
        rel_location=lambda s: f".claude/skills/{s['name']}/SKILL.md",
    )
    return _env().get_template("claude.md.j2").render(skills_xml=skills_xml)


def generate_agents_md(skills: list[dict], project_dir: Path) -> str:
    skills_xml = generate_skills_xml(
        skills,
        project_dir,
        rel_location=lambda s: f".skillet/skills/{s['name']}/SKILL.md",
    )
    return _env().get_template("agents.md.j2").render(skills_xml=skills_xml)


def generate_gemini_md(skills: list[dict], project_dir: Path) -> str:
    skills_xml = generate_skills_xml(
        skills,
        project_dir,
        rel_location=lambda s: f".skillet/skills/{s['name']}/SKILL.md",
    )
    return _env().get_template("gemini.md.j2").render(skills_xml=skills_xml)


def generate_skillet_mdc(skills: list[dict]) -> str:
    entries = []
    for s in sorted(skills, key=lambda x: x["name"].lower()):
        rel = f".skillet/skills/{s['name']}/SKILL.md"
        entries.append(
            {"name": s["name"], "description": s["description"], "rel_path": rel}
        )
    return _env().get_template("skillet.mdc.j2").render(skills=entries)


def write_config_files(skills_dir: Path, project_dir: Path, config: dict) -> dict:
    """Write IDE-facing config files. Returns map of logical name -> path written."""
    _remove_legacy_ide_files(project_dir)
    skills = get_skills_from_directory(skills_dir)
    result: dict[str, str] = {}

    if config.get("claude"):
        emit_claude_code_skills(skills_dir, project_dir)
        path = project_dir / "CLAUDE.md"
        path.write_text(generate_claude_md(skills, project_dir), encoding="utf-8")
        result["CLAUDE.md"] = str(path)
        result[".claude/skills/"] = str(project_dir / ".claude" / "skills")

    if config.get("cursor"):
        rules_dir = project_dir / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        path = rules_dir / "skillet.mdc"
        path.write_text(generate_skillet_mdc(skills), encoding="utf-8")
        result[".cursor/rules/skillet.mdc"] = str(path)

    if config.get("opencode"):
        path = project_dir / "AGENTS.md"
        path.write_text(generate_agents_md(skills, project_dir), encoding="utf-8")
        result["AGENTS.md"] = str(path)

    if config.get("gemini"):
        path = project_dir / "GEMINI.md"
        path.write_text(generate_gemini_md(skills, project_dir), encoding="utf-8")
        result["GEMINI.md"] = str(path)

    return result
