import json
from pathlib import Path

import pytest

from skillet.installer.lock import (
    existing_mirrors,
    is_managed,
    load_lock,
    lock_path,
    record_skill,
    save_lock,
    unrecord_skill,
)


def test_load_lock_returns_empty_shape_when_missing(tmp_path: Path) -> None:
    assert load_lock(tmp_path) == {"version": 1, "skills": {}}


def test_load_lock_handles_invalid_json(tmp_path: Path) -> None:
    p = lock_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{invalid", encoding="utf-8")

    assert load_lock(tmp_path) == {"version": 1, "skills": {}}


def test_load_lock_non_object_payload_normalizes_to_empty(tmp_path: Path) -> None:
    p = lock_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("[]", encoding="utf-8")

    assert load_lock(tmp_path) == {"version": 1, "skills": {}}


def test_save_lock_normalizes_payload_shape(tmp_path: Path) -> None:
    save_lock(
        tmp_path,
        {
            "version": 99,
            "skills": {
                "alpha": {
                    "origin": 123,
                    "mirrors": [" .cursor/skills/alpha/SKILL.md ", 42, ""],
                },
                "": {"origin": "x", "mirrors": []},
            },
        },
    )

    assert load_lock(tmp_path) == {
        "version": 1,
        "skills": {
            "alpha": {
                "origin": "",
                "mirrors": [" .cursor/skills/alpha/SKILL.md "],
            }
        },
    }


def test_existing_mirrors_returns_empty_when_entry_not_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import skillet.installer.lock as lock_mod

    monkeypatch.setattr(
        lock_mod,
        "load_lock",
        lambda _project_dir: {"version": 1, "skills": {"x": "not-a-dict"}},
    )
    assert existing_mirrors(tmp_path, "x") == []


def test_existing_mirrors_returns_empty_when_mirrors_not_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import skillet.installer.lock as lock_mod

    monkeypatch.setattr(
        lock_mod,
        "load_lock",
        lambda _project_dir: {
            "version": 1,
            "skills": {"x": {"origin": "o", "mirrors": "nope"}},
        },
    )
    assert existing_mirrors(tmp_path, "x") == []


def test_record_and_is_managed_round_trip(tmp_path: Path) -> None:
    record_skill(
        tmp_path,
        "git-os",
        origin="bundled",
        mirrors=[".claude/skills/git-os/SKILL.md", "", ".cursor/skills/git-os/SKILL.md"],
    )

    assert is_managed(tmp_path, "git-os")
    payload = load_lock(tmp_path)
    assert payload["skills"]["git-os"]["origin"] == "bundled"
    assert payload["skills"]["git-os"]["mirrors"] == [
        ".claude/skills/git-os/SKILL.md",
        ".cursor/skills/git-os/SKILL.md",
    ]


def test_unrecord_skill_removes_mirrors_and_lock_entry(tmp_path: Path) -> None:
    file_mirror = tmp_path / ".cursor" / "skills" / "git-os" / "SKILL.md"
    file_mirror.parent.mkdir(parents=True, exist_ok=True)
    file_mirror.write_text("managed", encoding="utf-8")

    dir_mirror = tmp_path / ".agents" / "skills" / "git-os"
    dir_mirror.mkdir(parents=True, exist_ok=True)
    (dir_mirror / "SKILL.md").write_text("managed", encoding="utf-8")

    record_skill(
        tmp_path,
        "git-os",
        origin="bundled",
        mirrors=[
            file_mirror.relative_to(tmp_path).as_posix(),
            dir_mirror.relative_to(tmp_path).as_posix(),
        ],
    )

    removed = unrecord_skill(tmp_path, "git-os")

    assert file_mirror in removed
    assert dir_mirror in removed
    assert not file_mirror.exists()
    assert not dir_mirror.exists()
    assert not is_managed(tmp_path, "git-os")
    assert lock_path(tmp_path).is_file()


def test_unrecord_skill_handles_invalid_entry_shapes(tmp_path: Path) -> None:
    p = lock_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {"version": 1, "skills": {"x": "not-a-dict", "y": {"origin": "o", "mirrors": "bad"}}}
        ),
        encoding="utf-8",
    )

    assert unrecord_skill(tmp_path, "x") == []
    assert unrecord_skill(tmp_path, "y") == []


def test_unrecord_skill_skips_invalid_mirror_items(tmp_path: Path) -> None:
    p = lock_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"version": 1, "skills": {"x": {"origin": "o", "mirrors": [None, "", "  "]}}}),
        encoding="utf-8",
    )

    assert unrecord_skill(tmp_path, "x") == []


def test_unrecord_skill_defensive_branches_with_malformed_loaded_lock(
    tmp_path: Path, monkeypatch
) -> None:
    import skillet.installer.lock as lock_mod

    # entry is not a dict -> early return branch
    monkeypatch.setattr(
        lock_mod,
        "load_lock",
        lambda _project_dir: {"version": 1, "skills": {"x": "bad-entry"}},
    )
    monkeypatch.setattr(lock_mod, "save_lock", lambda _project_dir, _payload: None)
    assert unrecord_skill(tmp_path, "x") == []

    # mirrors is not a list -> early return branch
    monkeypatch.setattr(
        lock_mod,
        "load_lock",
        lambda _project_dir: {"version": 1, "skills": {"x": {"origin": "o", "mirrors": "bad"}}},
    )
    assert unrecord_skill(tmp_path, "x") == []

    # invalid mirror entries -> continue branch
    monkeypatch.setattr(
        lock_mod,
        "load_lock",
        lambda _project_dir: {
            "version": 1,
            "skills": {"x": {"origin": "o", "mirrors": [None, "", "  "]}},
        },
    )
    assert unrecord_skill(tmp_path, "x") == []
