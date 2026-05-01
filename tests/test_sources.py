import json
from pathlib import Path

import pytest

from skillet.sources.apply import apply_all_sources
from skillet.sources.store import (
    load_sources,
    remove_source_entry,
    sources_json_path,
    upsert_source,
)


def test_sources_roundtrip(tmp_path: Path) -> None:
    upsert_source(tmp_path, "a-skill", {"kind": "local", "path": "vendor/a"})
    assert load_sources(tmp_path) == {"a-skill": {"kind": "local", "path": "vendor/a"}}

    upsert_source(tmp_path, "b-skill", {"kind": "http_zip", "url": "https://example.com/z.zip"})
    loaded = load_sources(tmp_path)
    assert len(loaded) == 2
    assert loaded["b-skill"]["kind"] == "http_zip"

    assert remove_source_entry(tmp_path, "a-skill") is True
    assert "a-skill" not in load_sources(tmp_path)

    assert remove_source_entry(tmp_path, "missing") is False


def test_remove_last_source_unlinks_file(tmp_path: Path) -> None:
    upsert_source(tmp_path, "only", {"kind": "local", "path": "x"})
    path = sources_json_path(tmp_path)
    assert path.is_file()
    assert remove_source_entry(tmp_path, "only") is True
    assert not path.exists()


def test_load_sources_invalid_json(tmp_path: Path) -> None:
    p = sources_json_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("not json", encoding="utf-8")
    assert load_sources(tmp_path) == {}


def test_load_sources_filters_non_objects(tmp_path: Path) -> None:
    p = sources_json_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"ok": {"kind": "local", "path": "."}, "bad": "skip", "no_kind": {}}),
        encoding="utf-8",
    )
    assert load_sources(tmp_path) == {"ok": {"kind": "local", "path": "."}}


def test_apply_github_skill(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    skill = tmp_path / "fetched" / "gh-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: gh-skill\ndescription: d\n---\n", encoding="utf-8"
    )

    def fake_fetch(source, *, token=None, client=None):
        return [skill], lambda: None

    import skillet.sources.apply as apply_mod
    monkeypatch.setattr(apply_mod, "fetch_github_skill_directories", fake_fetch)

    skills_dest = tmp_path / ".skillet" / "skills"
    upsert_source(
        tmp_path,
        "gh-skill",
        {"kind": "github", "source": "demo/repo"},
    )
    errors, summary = apply_all_sources(tmp_path, skills_dest, github_token=None)
    assert errors == []
    assert summary.added == ("gh-skill",)
    assert summary.removed == ()
    assert summary.unchanged == ()
    assert (skills_dest / "gh-skill" / "SKILL.md").is_file()


def test_apply_local_skill(tmp_path: Path) -> None:
    ext = tmp_path / "external" / "my-skill"
    ext.mkdir(parents=True)
    (ext / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: test\n---\n", encoding="utf-8"
    )

    skills_dest = tmp_path / ".skillet" / "skills"
    upsert_source(tmp_path, "my-skill", {"kind": "local", "path": "external/my-skill"})
    errors, summary = apply_all_sources(tmp_path, skills_dest)
    assert errors == []
    assert summary.added == ("my-skill",)
    assert summary.removed == ()
    assert summary.unchanged == ()
    assert (skills_dest / "my-skill" / "SKILL.md").is_file()


def test_apply_local_skill_from_repo_skills_source_key(tmp_path: Path) -> None:
    bundled = tmp_path / "skills" / "git-os"
    bundled.mkdir(parents=True)
    (bundled / "SKILL.md").write_text(
        "---\nname: git-os\ndescription: bundled local\n---\n", encoding="utf-8"
    )

    skills_dest = tmp_path / ".skillet" / "skills"
    upsert_source(tmp_path, "git-os", {"kind": "local", "source": "git-os"})
    errors, summary = apply_all_sources(tmp_path, skills_dest)
    assert errors == []
    assert summary.added == ("git-os",)
    assert summary.removed == ()
    assert summary.unchanged == ()
    assert (skills_dest / "git-os" / "SKILL.md").is_file()


def test_apply_all_sources_prunes_skills_removed_from_sources_json(
    tmp_path: Path,
) -> None:
    bundled = tmp_path / "skills" / "git-os"
    bundled.mkdir(parents=True)
    (bundled / "SKILL.md").write_text(
        "---\nname: git-os\ndescription: bundled\n---\n", encoding="utf-8"
    )

    skills_dest = tmp_path / ".skillet" / "skills"
    skills_dest.mkdir(parents=True)
    orphan = skills_dest / "soultrace"
    orphan.mkdir()
    (orphan / "SKILL.md").write_text(
        "---\nname: soultrace\ndescription: x\n---\n", encoding="utf-8"
    )

    upsert_source(tmp_path, "git-os", {"kind": "local", "source": "git-os"})
    errors, summary = apply_all_sources(tmp_path, skills_dest)
    assert errors == []
    assert (skills_dest / "git-os" / "SKILL.md").is_file()
    assert not (skills_dest / "soultrace").exists()
    assert summary.added == ("git-os",)
    assert summary.removed == ("soultrace",)
    assert summary.unchanged == ()


def test_apply_all_sources_second_run_marks_unchanged(tmp_path: Path) -> None:
    bundled = tmp_path / "skills" / "git-os"
    bundled.mkdir(parents=True)
    (bundled / "SKILL.md").write_text(
        "---\nname: git-os\ndescription: bundled\n---\n", encoding="utf-8"
    )
    skills_dest = tmp_path / ".skillet" / "skills"
    upsert_source(tmp_path, "git-os", {"kind": "local", "source": "git-os"})
    first_errors, first_summary = apply_all_sources(tmp_path, skills_dest)
    assert first_errors == []
    assert first_summary.added == ("git-os",)
    assert first_summary.unchanged == ()

    second_errors, second_summary = apply_all_sources(tmp_path, skills_dest)
    assert second_errors == []
    assert second_summary.added == ()
    assert second_summary.removed == ()
    assert second_summary.unchanged == ("git-os",)
