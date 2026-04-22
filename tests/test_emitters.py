import shutil
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


def test_write_config_files_claude_cursor_native_skills(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "alpha-skill", "Does alpha things")

    cfg = {
        "claude": True,
        "cursor": True,
        "gemini": True,
        "opencode": False,
    }
    written = write_config_files(skills_dir, tmp_path, cfg)

    for base in (".claude/skills/", ".cursor/skills/", ".agents/skills/"):
        assert (tmp_path / base.rstrip("/") / "alpha-skill" / "SKILL.md").is_file()

    assert written[".claude/skills/"] == str(tmp_path / ".claude" / "skills")
    assert written[".cursor/skills/"] == str(tmp_path / ".cursor" / "skills")
    assert written[".agents/skills/"] == str(tmp_path / ".agents" / "skills")


def test_prunes_outputs_when_ide_disabled(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "x", "y")

    (tmp_path / "AGENTS.md").write_text("user agents", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("user claude", encoding="utf-8")
    (tmp_path / "GEMINI.md").write_text("user gemini", encoding="utf-8")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": True, "cursor": True, "gemini": True, "opencode": True},
    )
    assert (tmp_path / ".claude" / "skills" / "x" / "SKILL.md").is_file()
    assert (tmp_path / ".cursor" / "skills" / "x" / "SKILL.md").is_file()
    assert (tmp_path / ".agents" / "skills" / "x" / "SKILL.md").is_file()

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "gemini": False, "opencode": False},
    )

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "user agents"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "user claude"
    assert (tmp_path / "GEMINI.md").read_text(encoding="utf-8") == "user gemini"
    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".cursor" / "skills").exists()
    assert not (tmp_path / ".agents" / "skills").exists()


def test_prunes_emitted_skill_when_source_skill_removed(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "stay", "s")
    _write_skill(skills_dir, "gone", "g")

    cfg = {
        "claude": True,
        "cursor": True,
        "gemini": False,
        "opencode": True,
    }
    write_config_files(skills_dir, tmp_path, cfg)

    assert (tmp_path / ".claude" / "skills" / "gone" / "SKILL.md").is_file()
    assert (tmp_path / ".cursor" / "skills" / "gone" / "SKILL.md").is_file()
    assert (tmp_path / ".agents" / "skills" / "gone" / "SKILL.md").is_file()

    shutil.rmtree(skills_dir / "gone")
    write_config_files(skills_dir, tmp_path, cfg)

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert not (tmp_path / base / "gone").exists()
        assert (tmp_path / base / "stay" / "SKILL.md").is_file()


def test_opencode_only_emits_agents_skills_dir_not_claude(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "solo", "solo skill")

    written = write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "gemini": False, "opencode": True},
    )

    assert (tmp_path / ".agents" / "skills" / "solo" / "SKILL.md").is_file()
    assert written[".agents/skills/"] == str(tmp_path / ".agents" / "skills")


def test_gemini_only_emits_agents_skills_dir(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "g", "g skill")

    written = write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "gemini": True, "opencode": False},
    )

    assert (tmp_path / ".agents" / "skills" / "g" / "SKILL.md").is_file()
    assert written[".agents/skills/"] == str(tmp_path / ".agents" / "skills")
    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".cursor" / "skills").exists()


def test_disabling_gemini_keeps_agents_skills_when_opencode_enabled(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "x", "y")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "gemini": True, "opencode": True},
    )
    assert (tmp_path / ".agents" / "skills" / "x" / "SKILL.md").is_file()

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "gemini": False, "opencode": True},
    )
    assert (tmp_path / ".agents" / "skills" / "x" / "SKILL.md").is_file()


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
