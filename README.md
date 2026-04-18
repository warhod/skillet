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

# Configure API keys (optional GitHub token for private sources / rate limits)
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
- **Multi-IDE Support**: Emits native-style files for Claude Code, Cursor, OpenCode, and Gemini
- **Sources**: Record skills from local paths or URLs in `.skillet/sources.json` (GitHub specs planned)
- **Interactive Config**: Guided setup for API keys and optional `GITHUB_TOKEN`

## Bundled Skills

| Skill | Description |
|-------|-------------|
| `git-os` | Conventional commits, atomic changes, pre-push checklist |
| `sprint` | Ticket-to-PR automation with branch and description templates |
| `deploy-checklist` | Pre/post deployment verification checklist |

## Configuration

Run `skillet config` to set up:
- OpenRouter API key
- Anthropic API key
- GitHub token (optional; helps with private repos and API rate limits)

## License

MIT