import json
import shutil
from pathlib import Path

import pytest

from skillet.installer.emitters import (
    _iter_lock_skill_entries,
    _remove_mirror_from_lock_entries,
    _tracked_mirror_dirs,
    emit_claude_code_skills,
    emit_native_skills,
    write_config_files,
)
from skillet.installer.lock import lock_path


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


def test_write_config_files_mirrors_all_enabled_targets(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "alpha-skill", "Does alpha things")

    cfg = {"claude": True, "cursor": True, "opencode": True}
    written = write_config_files(skills_dir, tmp_path, cfg)

    for base in (".claude/skills/", ".cursor/skills/", ".agents/skills/"):
        assert (tmp_path / base.rstrip("/") / "alpha-skill" / "SKILL.md").is_file()

    assert written[".claude/skills/"] == str(tmp_path / ".claude" / "skills")
    assert written[".cursor/skills/"] == str(tmp_path / ".cursor" / "skills")
    assert written[".agents/skills/"] == str(tmp_path / ".agents" / "skills")


def test_prunes_native_trees_when_targets_disabled(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "x", "y")

    (tmp_path / "USER_NOTES.md").write_text("keep me", encoding="utf-8")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": True, "cursor": True, "opencode": True},
    )
    assert (tmp_path / ".claude" / "skills" / "x" / "SKILL.md").is_file()
    assert (tmp_path / ".cursor" / "skills" / "x" / "SKILL.md").is_file()
    assert (tmp_path / ".agents" / "skills" / "x" / "SKILL.md").is_file()
    assert (tmp_path / "USER_NOTES.md").read_text(encoding="utf-8") == "keep me"

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False},
    )

    assert (tmp_path / "USER_NOTES.md").read_text(encoding="utf-8") == "keep me"
    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".cursor" / "skills").exists()
    assert not (tmp_path / ".agents" / "skills").exists()


def test_prunes_emitted_skill_when_source_skill_removed(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "stay", "s")
    _write_skill(skills_dir, "gone", "g")

    cfg = {"claude": True, "cursor": True, "opencode": True}
    write_config_files(skills_dir, tmp_path, cfg)

    assert (tmp_path / ".claude" / "skills" / "gone" / "SKILL.md").is_file()
    assert (tmp_path / ".cursor" / "skills" / "gone" / "SKILL.md").is_file()
    assert (tmp_path / ".agents" / "skills" / "gone" / "SKILL.md").is_file()

    shutil.rmtree(skills_dir / "gone")
    write_config_files(skills_dir, tmp_path, cfg)

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert not (tmp_path / base / "gone").exists()
        assert (tmp_path / base / "stay" / "SKILL.md").is_file()


def test_only_opencode_mirrors_agents_skills(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "solo", "solo skill")

    written = write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": True},
    )

    assert (tmp_path / ".agents" / "skills" / "solo" / "SKILL.md").is_file()
    assert written[".agents/skills/"] == str(tmp_path / ".agents" / "skills")
    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".cursor" / "skills").exists()


def test_qwen_mirrors_dot_qwen_skills(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "qw", "q skill")

    written = write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False, "qwen": True},
    )

    assert (tmp_path / ".qwen" / "skills" / "qw" / "SKILL.md").is_file()
    assert written[".qwen/skills/"] == str(tmp_path / ".qwen" / "skills")
    assert not (tmp_path / ".agents" / "skills").exists()


def test_agents_skills_kept_when_cline_on_but_opencode_off(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "c", "c skill")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False, "cline": True},
    )
    assert (tmp_path / ".agents" / "skills" / "c" / "SKILL.md").is_file()

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False, "cline": False},
    )
    assert not (tmp_path / ".agents" / "skills").exists()


def test_no_targets_enabled_returns_empty_written_and_prunes_mirrors(
    tmp_path: Path,
) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "g", "g skill")

    written = write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False},
    )

    assert written == {}
    assert not (tmp_path / ".agents" / "skills").exists()
    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".cursor" / "skills").exists()


def test_write_config_files_removes_legacy_skillet_paths(tmp_path: Path) -> None:
    """``write_config_files`` still deletes paths listed in emitters legacy cleanup."""
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "s", "d")
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "skillet.mdc").write_text("old", encoding="utf-8")
    gh = tmp_path / ".github"
    gh.mkdir(parents=True)
    (gh / "copilot-instructions.md").write_text("old", encoding="utf-8")

    write_config_files(skills_dir, tmp_path, {"claude": True, "cursor": False, "opencode": False})

    assert not (rules / "skillet.mdc").exists()
    assert not gh.exists()
    assert (tmp_path / ".claude" / "skills" / "s" / "SKILL.md").is_file()


def test_emit_native_skills_prunes_stale_mirror_dirs(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "keep", "k")
    dest = tmp_path / "mirror"
    dest.mkdir(parents=True)
    stale = dest / "removed"
    stale.mkdir(parents=True)
    (stale / "SKILL.md").write_text("stale", encoding="utf-8")

    emit_native_skills(skills_dir, dest)

    assert not stale.exists()
    assert (dest / "keep" / "SKILL.md").is_file()
    assert (dest / "keep" / "SKILL.md").read_text(encoding="utf-8") == (
        skills_dir / "keep" / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_emit_native_skills_overwrites_when_source_changes(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "mut", "first")
    dest = tmp_path / "out"
    emit_native_skills(skills_dir, dest)
    first = (dest / "mut" / "SKILL.md").read_text(encoding="utf-8")
    assert "first" in first

    (skills_dir / "mut" / "SKILL.md").write_text(
        "---\nname: mut\ndescription: second\n---\n\n# updated\n",
        encoding="utf-8",
    )
    emit_native_skills(skills_dir, dest)
    assert "second" in (dest / "mut" / "SKILL.md").read_text(encoding="utf-8")
    assert "updated" in (dest / "mut" / "SKILL.md").read_text(encoding="utf-8")
    assert (dest / "mut" / "SKILL.md").read_text(encoding="utf-8") != first


def test_prune_single_target_leaves_other_native_trees(tmp_path: Path) -> None:
    """Disabling only Cursor removes ``.cursor/skills`` but keeps Claude/OpenCode mirrors."""
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "one", "o")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": True, "cursor": True, "opencode": True},
    )
    assert (tmp_path / ".cursor" / "skills" / "one" / "SKILL.md").is_file()

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": True, "cursor": False, "opencode": True},
    )

    assert not (tmp_path / ".cursor" / "skills").exists()
    assert (tmp_path / ".claude" / "skills" / "one" / "SKILL.md").is_file()
    assert (tmp_path / ".agents" / "skills" / "one" / "SKILL.md").is_file()


def test_user_managed_native_skill_survives_prune_cycles(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "managed", "by skillet")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": True, "opencode": False},
    )
    assert (tmp_path / ".cursor" / "skills" / "managed" / "SKILL.md").is_file()

    user_skill = tmp_path / ".cursor" / "skills" / "my-custom"
    user_skill.mkdir(parents=True, exist_ok=True)
    (user_skill / "SKILL.md").write_text("user placed", encoding="utf-8")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False},
    )

    assert not (tmp_path / ".cursor" / "skills" / "managed").exists()
    assert (tmp_path / ".cursor" / "skills" / "my-custom" / "SKILL.md").is_file()


def test_iter_lock_skill_entries_skips_non_dict_skills_container() -> None:
    assert _iter_lock_skill_entries({"skills": "bad"}) == []


def test_remove_mirror_skips_non_list_mirrors() -> None:
    entries = [{"mirrors": "not-a-list"}]
    assert _remove_mirror_from_lock_entries(entries, "any") is False


def test_tracked_mirror_dirs_skips_bad_mirror_entries(tmp_path: Path) -> None:
    dest = tmp_path / ".cursor" / "skills"
    entries = [
        {"mirrors": "not-list"},
        {"mirrors": ["", "  ", 99, ".cursor/skills/a/SKILL.md"]},
    ]
    tracked = _tracked_mirror_dirs(entries, dest, tmp_path)
    assert tracked == {".cursor/skills/a"}


def test_write_config_files_skips_agent_without_native_mirror_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import skillet.installer.emitters as emitters_mod

    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "solo", "s")

    mapping = dict(emitters_mod.AGENT_NATIVE_SKILL_REL_PATH)
    mapping["claude"] = None
    monkeypatch.setattr(emitters_mod, "AGENT_NATIVE_SKILL_REL_PATH", mapping)

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": True, "cursor": False, "opencode": False},
    )

    assert not (tmp_path / ".claude" / "skills").exists()


def test_write_config_files_dedupes_shared_native_root(tmp_path: Path) -> None:
    """Gemini and OpenCode share ``.agents/skills``; second agent must not double-emit."""
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "d", "d")

    written = write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": True, "gemini": True},
    )

    assert written == {".agents/skills/": str(tmp_path / ".agents" / "skills")}
    assert (tmp_path / ".agents" / "skills" / "d" / "SKILL.md").is_file()


def test_prune_disabled_skips_non_directory_entries_under_tree(
    tmp_path: Path,
) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "z", "z")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": True, "opencode": False},
    )
    assert (tmp_path / ".cursor" / "skills" / "z" / "SKILL.md").is_file()

    junk = tmp_path / ".cursor" / "skills" / "notes.txt"
    junk.write_text("keep", encoding="utf-8")

    write_config_files(
        skills_dir,
        tmp_path,
        {"claude": False, "cursor": False, "opencode": False},
    )

    assert not (tmp_path / ".cursor" / "skills" / "z").exists()
    assert junk.is_file()


def test_emit_native_skills_resets_non_list_mirrors_in_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import skillet.installer.emitters as emitters_mod

    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "fix", "f")
    dest = tmp_path / ".cursor" / "skills"

    def _load(_project: Path) -> dict:
        return {
            "version": 1,
            "skills": {"fix": {"origin": "o", "mirrors": "broken"}},
        }

    monkeypatch.setattr(emitters_mod, "load_lock", _load)
    emit_native_skills(skills_dir, dest, tmp_path)
    saved = json.loads(lock_path(tmp_path).read_text(encoding="utf-8"))
    mirrors = saved["skills"]["fix"]["mirrors"]
    assert isinstance(mirrors, list)
    assert any(m.endswith("fix/SKILL.md") for m in mirrors)


def test_emit_claude_code_skills_writes_under_claude_skills(tmp_path: Path) -> None:
    skills_dir = tmp_path / ".skillet" / "skills"
    _write_skill(skills_dir, "c", "claude skill")

    emit_claude_code_skills(skills_dir, tmp_path)

    out = tmp_path / ".claude" / "skills" / "c" / "SKILL.md"
    assert out.is_file()
    assert "claude skill" in out.read_text(encoding="utf-8")
