import json
from pathlib import Path

from click.testing import CliRunner

from skillet.cli import main


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
