# Open Skills

AI agent skills for developer workflows — git discipline, PR automation, and skill management.

## Installation

```bash
pip install open-skills
```

## Quick Start

```bash
# Install skills into current project
open-skills install

# List installed skills
open-skills list

# Search for a skill
open-skills search "git"

# Configure API keys and registry
open-skills config

# Re-sync IDE configs
open-skills sync
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

Run `open-skills config` to set up:
- Registry URL
- OpenRouter API key
- Anthropic API key
- GitHub token

## License

MIT