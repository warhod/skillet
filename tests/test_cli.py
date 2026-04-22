import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillet.cli import main
from skillet.config.project import PROJECT_CONFIG_VERSION, save_project_config


def _ensure_all_native_targets(project_dir: Path) -> None:
    save_project_config(
        project_dir,
        {
            "version": PROJECT_CONFIG_VERSION,
            "ide_support": ["claude", "cursor", "opencode"],
        },
    )


def test_install_writes_project_config_and_skills(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["install", str(tmp_path)])
    assert result.exit_code == 0, result.output

    cfg_path = tmp_path / ".skillet" / "config" / "config.json"
    assert cfg_path.is_file()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data.get("version") == "1"
    assert isinstance(data.get("ide_support"), list)
    assert data["ide_support"]

    skills_dir = tmp_path / ".skillet" / "skills"
    assert (skills_dir / "git-os" / "SKILL.md").is_file()


def test_install_removed_flags_raise_usage_error() -> None:
    runner = CliRunner()
    for args in (["install", "--all"], ["install", "--with-hooks"]):
        r = runner.invoke(main, args)
        assert r.exit_code != 0


def test_install_mirrors_native_skill_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_ide_support",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    result = runner.invoke(main, ["install", str(tmp_path)])
    assert result.exit_code == 0, result.output

    for name in ("git-os", "sprint", "deploy-checklist"):
        for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
            assert (tmp_path / base / name / "SKILL.md").is_file()

    assert not (tmp_path / ".cursor/rules/skillet.mdc").exists()
    assert not (tmp_path / "AGENTS.md").exists()


def test_sync_prunes_native_mirrors_when_skill_removed_from_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_ide_support",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    assert runner.invoke(main, ["install", str(tmp_path)]).exit_code == 0

    shutil.rmtree(tmp_path / ".skillet" / "skills" / "git-os")
    r = runner.invoke(main, ["sync", str(tmp_path)])
    assert r.exit_code == 0, r.output

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert not (tmp_path / base / "git-os").exists()
        assert (tmp_path / base / "sprint" / "SKILL.md").is_file()


def test_remove_prunes_skill_from_all_native_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_ide_support",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    assert runner.invoke(main, ["install", str(tmp_path)]).exit_code == 0

    r = runner.invoke(main, ["remove", "git-os", str(tmp_path)])
    assert r.exit_code == 0, r.output

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert not (tmp_path / base / "git-os").exists()


def test_sync_strips_legacy_skillet_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "skillet.cli.ensure_project_ide_support",
        _ensure_all_native_targets,
    )
    runner = CliRunner()
    assert runner.invoke(main, ["install", str(tmp_path)]).exit_code == 0

    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / "skillet.mdc").write_text("legacy", encoding="utf-8")

    assert runner.invoke(main, ["sync", str(tmp_path)]).exit_code == 0

    assert not (rules / "skillet.mdc").exists()


def test_add_local_skill_mirrors_to_native_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["install", "--skip-config", str(tmp_path)]).exit_code == 0
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
