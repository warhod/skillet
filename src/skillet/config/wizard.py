"""Interactive global configuration (questionary)."""

from __future__ import annotations

import questionary

from skillet.config.settings import (
    IDE_KEYS,
    IDE_LABELS,
    get_config_path,
    ide_checkbox_instruction,
    ide_multiselect_prompt_global,
    ide_reference_hint_line,
    load_config,
    save_config,
)


def prompt_ide_targets(
    *,
    message: str,
    hint_previous_keys: list[str] | None = None,
) -> list[str]:
    """Multi-select IDE keys; all rows start unchecked; at least one required."""
    full_message = message.rstrip()
    if hint_previous_keys:
        hint = ide_reference_hint_line(hint_previous_keys)
        if hint:
            full_message = f"{full_message}\n{hint}"

    choices = [
        {"name": IDE_LABELS[k], "value": k, "checked": False} for k in IDE_KEYS
    ]

    def _need_at_least_one(selected: list[str]) -> bool | str:
        if len(selected) >= 1:
            return True
        return (
            "Select at least one IDE (Space toggles a row, Enter confirms). "
            "You cannot continue with none selected."
        )

    while True:
        picked = questionary.checkbox(
            full_message,
            choices=choices,
            validate=_need_at_least_one,
            instruction=ide_checkbox_instruction(),
        ).ask()
        if picked is None:
            raise KeyboardInterrupt
        filtered = [p for p in picked if p in IDE_LABELS]
        if filtered:
            return filtered


def _ask_text(message: str, default: str) -> str:
    ans = questionary.text(message, default=default).ask()
    if ans is None:
        return default
    return ans


def run_config_wizard() -> None:
    """Interactive wizard: default IDE targets and optional GitHub token for Skillet."""
    config_path_existed = get_config_path().exists()
    config = load_config()

    prior = config.get("ide_support")
    if not isinstance(prior, list) or not prior:
        prior = list(IDE_KEYS)
    prior_norm = [k for k in prior if k in IDE_LABELS]
    ide_selected = prompt_ide_targets(
        message=ide_multiselect_prompt_global(),
        hint_previous_keys=prior_norm if config_path_existed else None,
    )
    config["ide_support"] = ide_selected

    config["github_token"] = _ask_text(
        "GitHub token (optional; private skill repos and API limits for `skillet add`):",
        config.get("github_token", "") or "",
    )

    save_config(config)

    _print_config_wizard_footer(config)


def _print_config_wizard_footer(config: dict) -> None:
    print("\n✓ Configuration saved to ~/.config/skillet/config.json")

    print(
        "\nSkillet reads `GITHUB_TOKEN` from the environment or this file when "
        "fetching GitHub skill sources. Set it in `.env` or your shell if you prefer."
    )
    print("  GITHUB_TOKEN — optional")

    if (config.get("github_token") or "").strip():
        print(
            "\nA token was saved in ~/.config/skillet/config.json. "
        )
    else:
        print("\nNo GitHub token was entered; add one when you use private `skillet add` sources.")
