from pathlib import Path

from skillet.installer.emitters import write_config_files


def _write_skill(skills_dir: Path, name: str, description: str) -> None:
    d = skills_dir / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"""---
name: {name}
description: {description}
---

# {name}
""",
        encoding="utf-8",
    )


def test_write_config_files_all_targets(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "alpha-skill", "Does alpha things")

    cfg = {
        "claude": True,
        "cursor": True,
        "opencode": True,
        "gemini": True,
    }
    written = write_config_files(skills_dir, tmp_path, cfg)

    assert (tmp_path / ".claude" / "skills" / "alpha-skill" / "SKILL.md").is_file()
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert ".claude/skills/alpha-skill/SKILL.md" in claude_md
    assert "<available_skills>" in claude_md

    mdc = (tmp_path / ".cursor" / "rules" / "skillet.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: true" in mdc
    assert ".skillet/skills/alpha-skill/SKILL.md" in mdc
    assert "**alpha-skill**" in mdc

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert ".skillet/skills/alpha-skill/SKILL.md" in agents

    gemini = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
    assert ".skillet/skills/alpha-skill/SKILL.md" in gemini

    assert "CLAUDE.md" in written
    assert ".cursor/rules/skillet.mdc" in written


def test_removes_legacy_cursorrules_and_copilot(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "x", "y")

    legacy = tmp_path / ".cursorrules"
    legacy.write_text("old", encoding="utf-8")
    gh = tmp_path / ".github"
    gh.mkdir(parents=True)
    copilot = gh / "copilot-instructions.md"
    copilot.write_text("old", encoding="utf-8")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": True, "opencode": False, "gemini": False},
    )

    assert not legacy.exists()
    assert not copilot.exists()


def test_prunes_outputs_when_ide_disabled(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "x", "y")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": True, "cursor": True, "opencode": True, "gemini": True},
    )
    assert (tmp_path / "AGENTS.md").is_file()

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False, "gemini": False},
    )

    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".cursor" / "rules" / "skillet.mdc").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "GEMINI.md").exists()


def test_skills_xml_escapes_markup(tmp_path: Path) -> None:
    from skillet.skills.parser import generate_skills_xml

    skills = [
        {
            "name": "a",
            "description": 'Use <script> & "quotes"',
            "skill_file": str(tmp_path / "a" / "SKILL.md"),
        }
    ]
    xml = generate_skills_xml(skills, tmp_path, rel_location=lambda s: "p<th>ath")
    assert "<script>" not in xml
    assert "&lt;script&gt;" in xml
    assert "&amp;" in xml
