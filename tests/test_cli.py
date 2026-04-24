import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillet.cli import _materialize_summary_lines, _sync_footer, main
from skillet.sources import MaterializeSummary
from skillet.config.project import PROJECT_CONFIG_VERSION, save_project_config
from skillet.sources.store import load_sources, save_sources


def _write_local_repo_skills(project_dir: Path) -> None:
    for name in ("git-os", "sprint", "deploy-checklist"):
        d = project_dir / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: seeded\n---\n",
            encoding="utf-8",
        )


def _ensure_all_native_targets(project_dir: Path) -> None:
    save_project_config(
        project_dir,
        {
            "version": PROJECT_CONFIG_VERSION,
            "agent": ["claude", "cursor", "opencode"],
        },
    )


def test_init_writes_project_config_and_skills(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_repo_skills(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    cfg_path = tmp_path / ".skillet" / "config" / "config.json"
    assert cfg_path.is_file()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data.get("version") == "1"
    assert isinstance(data.get("agent"), list)
    assert data["agent"]

    skills_dir = tmp_path / ".skillet" / "skills"
    assert (skills_dir / "git-os" / "SKILL.md").is_file()
    sources = load_sources(tmp_path)
    assert sources["git-os"] == {"kind": "local", "source": "git-os"}


def test_init_uses_sources_json_as_single_source_of_truth(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "vendor" / "extra-skill"
    custom.mkdir(parents=True)
    (custom / "SKILL.md").write_text(
        "---\nname: extra-skill\ndescription: extra\n---\n\n# Extra\n",
        encoding="utf-8",
    )
    save_sources(
        tmp_path,
        {"extra-skill": {"kind": "local", "path": "vendor/extra-skill"}},
    )

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--skip-config", str(tmp_path)])
    assert result.exit_code == 0, result.output

    skills_dir = tmp_path / ".skillet" / "skills"
    assert (skills_dir / "extra-skill" / "SKILL.md").is_file()


def test_init_removed_flags_raise_usage_error() -> None:
    runner = CliRunner()
    for args in (["init", "--all"], ["init", "--with-hooks"]):
        r = runner.invoke(main, args)
        assert r.exit_code != 0


def test_init_mirrors_native_skill_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_repo_skills(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_agents",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    for name in ("git-os", "sprint", "deploy-checklist"):
        for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
            assert (tmp_path / base / name / "SKILL.md").is_file()

    assert not (tmp_path / ".cursor/rules/skillet.mdc").exists()
    assert not (tmp_path / "AGENTS.md").exists()


def test_sync_restores_native_mirrors_from_sources_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_repo_skills(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_agents",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0

    shutil.rmtree(tmp_path / ".skillet" / "skills" / "git-os")
    r = runner.invoke(main, ["sync", str(tmp_path)])
    assert r.exit_code == 0, r.output

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert (tmp_path / base / "git-os" / "SKILL.md").is_file()
        assert (tmp_path / base / "sprint" / "SKILL.md").is_file()


def test_remove_prunes_skill_from_all_native_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_repo_skills(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_agents",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0

    r = runner.invoke(main, ["remove", "git-os", str(tmp_path)])
    assert r.exit_code == 0, r.output

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert not (tmp_path / base / "git-os").exists()


def test_remove_refuses_to_delete_unmanaged_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    unmanaged = tmp_path / ".skillet" / "skills" / "git-os"
    unmanaged.mkdir(parents=True, exist_ok=True)
    (unmanaged / "SKILL.md").write_text(
        "---\nname: git-os\ndescription: user skill\n---\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    r = runner.invoke(main, ["remove", "git-os", str(tmp_path)])

    assert r.exit_code == 0, r.output
    assert "is not managed by Skillet" in r.output
    assert unmanaged.exists()


def test_add_reports_unmanaged_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--skip-config", str(tmp_path)]).exit_code == 0

    unmanaged = tmp_path / ".skillet" / "skills" / "extra-skill"
    unmanaged.mkdir(parents=True, exist_ok=True)
    (unmanaged / "SKILL.md").write_text(
        "---\nname: extra-skill\ndescription: unmanaged\n---\n",
        encoding="utf-8",
    )

    ext = tmp_path / "vendor" / "extra-skill"
    ext.mkdir(parents=True)
    (ext / "SKILL.md").write_text(
        "---\nname: extra-skill\ndescription: external\n---\n",
        encoding="utf-8",
    )

    r = runner.invoke(main, ["add", "vendor/extra-skill", str(tmp_path)])

    assert r.exit_code == 0, r.output
    assert "skill already exists (not managed by Skillet), skipping" in r.output
    assert "Tracked" not in r.output


def test_sync_strips_legacy_skillet_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_repo_skills(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_agents",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0

    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / "skillet.mdc").write_text("legacy", encoding="utf-8")

    assert runner.invoke(main, ["sync", str(tmp_path)]).exit_code == 0

    assert not (rules / "skillet.mdc").exists()


def test_add_local_skill_mirrors_to_native_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_repo_skills(tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--skip-config", str(tmp_path)]).exit_code == 0
    _ensure_all_native_targets(tmp_path)
    assert runner.invoke(main, ["sync", str(tmp_path)]).exit_code == 0

    ext = tmp_path / "vendor" / "extra-skill"
    ext.mkdir(parents=True)
    (ext / "SKILL.md").write_text(
        "---\nname: extra-skill\ndescription: extra\n---\n\n# Extra\n",
        encoding="utf-8",
    )

    r = runner.invoke(main, ["add", "vendor/extra-skill", str(tmp_path)])
    assert r.exit_code == 0, r.output

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        p = tmp_path / base / "extra-skill" / "SKILL.md"
        assert p.is_file()
        assert "extra-skill" in p.read_text(encoding="utf-8")


def test_sync_footer_includes_error_count() -> None:
    assert _sync_footer([]) == "✓ Sync complete!"
    assert _sync_footer(["x"]) == "✓ Sync complete! (1 error during sync)"
    assert _sync_footer(["x", "y"]) == "✓ Sync complete! (2 errors during sync)"


def test_materialize_summary_lines_joins_buckets() -> None:
    s = MaterializeSummary(
        added=("a",),
        removed=("b",),
        unchanged=("c", "d"),
    )
    lines = _materialize_summary_lines(s, had_apply_errors=False)
    assert len(lines) == 1
    assert "added: a" in lines[0]
    assert "removed: b" in lines[0]
    assert "unchanged: c, d" in lines[0]
