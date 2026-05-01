"""Shared agent-target metadata and global user config (~/.config/skillet/config.json)."""

from __future__ import annotations

import json
from pathlib import Path

AGENT_KEYS = (
    "claude",
    "cursor",
    "gemini",
    "opencode",
    "antigravity",
    "cline",
    "codex",
    "copilot",
    "kimi",
    "qwen",
)

# Short product names (hints, reference lines).
AGENT_LABELS: dict[str, str] = {
    "claude": "Claude Code",
    "cursor": "Cursor",
    "gemini": "Gemini CLI",
    "opencode": "OpenCode",
    "antigravity": "Antigravity",
    "cline": "Cline",
    "codex": "Codex",
    "copilot": "GitHub Copilot",
    "kimi": "Kimi Code CLI",
    "qwen": "Qwen Code",
}

# Project-relative roots where Skillet mirrors each skill as ``<name>/SKILL.md``.
# Paths follow agentskills / Vercel agent layout conventions (project scope).
AGENT_NATIVE_SKILL_REL_PATH: dict[str, str | None] = {
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "gemini": ".agents/skills",
    "opencode": ".agents/skills",
    "antigravity": ".agents/skills",
    "cline": ".agents/skills",
    "codex": ".agents/skills",
    "copilot": ".agents/skills",
    "kimi": ".agents/skills",
    "qwen": ".qwen/skills",
}


def agent_multiselect_choice_label(agent_key: str) -> str:
    """One-line checkbox label: product name and native path (wizard / project prompts)."""
    if agent_key not in AGENT_LABELS:
        return agent_key
    name = AGENT_LABELS[agent_key]
    rel = AGENT_NATIVE_SKILL_REL_PATH.get(agent_key)
    if rel:
        return f"{name} — {rel}/"
    return f"{name} — (config only; no native skill mirror)"


def format_agent_target_mapping_summary(selected_keys: list[str]) -> str:
    """Human-readable summary of native mirror paths for the given ``agent`` key list."""
    path_order: list[str] = []
    path_to_names: dict[str, list[str]] = {}
    for key in AGENT_KEYS:
        if key not in selected_keys:
            continue
        rel = AGENT_NATIVE_SKILL_REL_PATH.get(key)
        if not rel:
            continue
        if rel not in path_to_names:
            path_order.append(rel)
            path_to_names[rel] = []
        path_to_names[rel].append(AGENT_LABELS[key])
    lines = [
        f"  • {', '.join(path_to_names[p])}: {p}/" for p in path_order
    ]
    if not lines:
        return ""
    return "Native skill directories for enabled agents:\n" + "\n".join(lines)


def normalize_agents(keys: list[str] | None) -> list[str]:
    """Drop unknown agent keys from stored lists."""
    if not isinstance(keys, list):
        return []
    return [k for k in keys if k in AGENT_KEYS]


def read_agents_from_mapping(m: dict) -> list[str]:
    """Resolve agent keys from ``agent``, then legacy ``agent_support`` or ``ide_support``."""
    for key in ("agent", "agent_support", "ide_support"):
        raw = m.get(key)
        if isinstance(raw, list) and raw:
            norm = normalize_agents(raw)
            if norm:
                return norm
    return []


def agent_checkbox_instruction() -> str:
    return "(Space = select, Enter = confirm; at least one required)"


def agent_multiselect_usage_line() -> str:
    return (
        "Nothing is pre-selected — press Space on each agent you use, then Enter."
    )


def agent_multiselect_prompt_global() -> str:
    return f"Which agents do you use?\n  {agent_multiselect_usage_line()}"


def agent_multiselect_prompt_project() -> str:
    return (
        "Which agents should this project target?\n"
        f"  {agent_multiselect_usage_line()}"
    )


def agent_reference_hint_line(keys: list[str]) -> str | None:
    labels = [AGENT_LABELS[k] for k in keys if k in AGENT_LABELS]
    if not labels:
        return None
    return (
        f"  (For reference: {', '.join(labels)} — use Space to select what applies.)"
    )


def get_config_path() -> Path:
    config_dir = Path.home() / ".config" / "skillet"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def _lean_config_from_raw(raw: dict | None) -> dict:
    """Only fields Skillet reads; strips legacy keys from older installs."""
    if not isinstance(raw, dict):
        raw = {}
    agents = read_agents_from_mapping(raw)
    if not agents:
        agents = list(AGENT_KEYS)
    token = raw.get("github_token")
    gh = token.strip() if isinstance(token, str) else ""
    return {"agent": agents, "github_token": gh}


def load_config() -> dict:
    path = get_config_path()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}
        return _lean_config_from_raw(raw)
    return _lean_config_from_raw({})


def save_config(config: dict) -> None:
    payload = _lean_config_from_raw(config)
    get_config_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
