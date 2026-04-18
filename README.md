# Skillet

Prepare and serve agent skills into your repo — for any workflow and any project.

## Installation

Skillet is not published on PyPI yet; install from a clone (a future PyPI release may use a name such as `agent-skillet`).

```bash
uv pip install -e .
```

## Quick Start

```bash
# Install skills into current project
skillet install

# List installed skills
skillet list

# Search for a skill
skillet search "git"

# Configure API keys and registry
skillet config

# Re-sync IDE configs
skillet sync
```

Alternatively, run with `uv run`:

```bash
uv run skillet install
```

## Features

- **Skills System**: Reusable markdown instructions for AI coding assistants
- **Multi-IDE Support**: Generates config for OpenCode, Cursor, and GitHub Copilot
- **Skill Registry**: Fetch additional skills from a remote registry
- **Interactive Config**: Guided setup for API keys and settings

## Bundled Skills

| Skill | Description |
|-------|-------------|
| `git-os` | Conventional commits, atomic changes, pre-push checklist |
| `sprint` | Ticket-to-PR automation with branch and description templates |
| `deploy-checklist` | Pre/post deployment verification checklist |

## Configuration

Run `skillet config` to set up:
- Registry URL
- OpenRouter API key
- Anthropic API key
- GitHub token

## License

MIT