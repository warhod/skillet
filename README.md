# Agent Skillet

[![CI](https://github.com/508-dev/agent-skillet/actions/workflows/ci.yml/badge.svg)](https://github.com/508-dev/agent-skillet/actions/workflows/ci.yml)

Prepare and serve agent skills!

Agent Skillet helps teams install, version, and sync agent skills inside a repository.

## Install

### From PyPI (recommended)

```bash
uvx agent-skillet init
uv tool install agent-skillet
```

### From source (development)

```bash
uv pip install -e .
```

If you do not already have `uv`, run:

```bash
zsh install.sh
```

## Quick Start

```text
Usage: skillet [OPTIONS] COMMAND [ARGS]...

  Skillet — initialize and sync agent skills into your repo

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  add     Add skills from a local skills directory or GitHub.
  config  Global defaults: agent targets and optional GitHub token for...
  init    Initialize Skillet in a directory, sync sources, mirror native...
  list    List all materialized skills.
  remove  Remove an installed skill.
  search  Search all skills by name or description.
  sync    Read sources from `.skillet/config/sources.json` and sync.
```

## How It Works

- Tracks installed skill sources in `.skillet/config/sources.json`.
- Materializes installed skills into `.skillet/skills/<name>/SKILL.md`.
- Mirrors enabled skills into agent-native directories (for example `.cursor/skills/` and `.claude/skills/`).
- Supports local sources and GitHub specs (`owner/repo`, `owner/repo/path@ref`).

### Example `sources.json`

```json
{
  "git-os": {
    "kind": "local",
    "source": "git-os"
  },
  "skill-creator": {
    "kind": "github",
    "spec": "anthropics/skills/skill-creator"
  }
}
```

## Common Commands

```bash
# Add a local skill directory
skillet add ./team-skills/react-frontend

# Add a GitHub skill source
skillet add some-org/shared-frontend-patterns

# Re-sync after changing sources
skillet sync
```

## Bundled Skills

- `git-os`: Conventional commits, atomic changes, pre-push checklist
- `sprint`: Ticket-to-PR automation with branch and description templates
- `deploy-checklist`: Pre/post deployment verification checklist

## Documentation

- [Authoring skills](docs/AUTHORING.md)
- [Releasing](docs/RELEASE.md)

## Contributing

Contributions are welcome and encouraged.

- Open an issue first for bug reports, feature requests, or design discussion.
- Keep pull requests focused and small; include clear context in the description.
- Add or update tests when behavior changes.
- Run local checks before opening a PR:

```bash
uv sync
ruff check
pytest
```

- Be respectful and collaborative in reviews so we can keep the project healthy and active!

## License

MIT
