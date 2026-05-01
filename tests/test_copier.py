from pathlib import Path

from skillet.installer.copier import copy_all_skills, copy_skill
from skillet.installer.lock import load_lock, record_skill


def _write_skill(parent: Path, name: str) -> None:
    d = parent / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")


def test_copy_skill_skips_unmanaged_destination_conflict(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _write_skill(src, "keep")

    dest_root = tmp_path / "dest"
    dest = dest_root / "keep"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("user-owned", encoding="utf-8")

    assert copy_skill(src / "keep", dest, project_dir=tmp_path) is False
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "user-owned"


def test_copy_all_skills_skips_when_copy_skill_returns_false(tmp_path: Path) -> None:
    src = tmp_path / "bundled"
    dest = tmp_path / ".skillet" / "skills"
    _write_skill(src, "a")
    _write_skill(src, "b")

    (dest / "b").mkdir(parents=True)
    (dest / "b" / "SKILL.md").write_text("user", encoding="utf-8")

    count = copy_all_skills(src, dest, project_dir=tmp_path)
    assert count == 1
    assert (dest / "a" / "SKILL.md").is_file()
    assert (dest / "b" / "SKILL.md").read_text(encoding="utf-8") == "user"


def test_copy_all_skills_records_with_existing_mirrors_when_present(tmp_path: Path) -> None:
    src = tmp_path / "bundled"
    dest = tmp_path / ".skillet" / "skills"
    _write_skill(src, "one")

    record_skill(
        tmp_path,
        "one",
        origin="prior",
        mirrors=[".claude/skills/one/SKILL.md"],
    )

    assert copy_all_skills(src, dest, project_dir=tmp_path) == 1
    assert load_lock(tmp_path)["skills"]["one"]["mirrors"] == [
        ".claude/skills/one/SKILL.md",
    ]
