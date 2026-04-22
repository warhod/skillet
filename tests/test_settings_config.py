import json
from pathlib import Path

import pytest

def test_save_config_writes_only_lean_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from skillet.config import settings

    fake = tmp_path / "config.json"
    monkeypatch.setattr(settings, "get_config_path", lambda: fake)
    settings.save_config(
        {
            "ide_support": ["cursor", "gemini"],
            "github_token": "tok",
            "anthropic_api_key": "noise",
        }
    )
    data = json.loads(fake.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"ide_support", "github_token"}
    assert data["github_token"] == "tok"
    assert data["ide_support"] == ["cursor", "gemini"]
