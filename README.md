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
- Supports local sources and GitHub specs (`owner/repo`, `owner/repo/subpath`, `owner/repo/subpath@ref`).

### Example `sources.json`

Each entry maps a skill name to its source. The `kind` field is either `"local"` or `"github"`.

```json
{
  "git-os": {
    "kind": "local",
    "source": "git-os"
  },
  "python-design-patterns": {
    "kind": "github",
    "source": "wshobson/agents/python-design-patterns@main"
  },
  "skill-creator": {
    "kind": "github",
    "source": "anthropics/skills/skill-creator"
  }
}
```

`skillet add` writes these entries for you — you rarely need to edit the file directly.

## Common Commands

```bash
# Install bundled skills and set up agent mirrors
skillet init

# Add a local skill directory (must contain SKILL.md)
skillet add ./team-skills/checkout-flow

# Add a single skill from a GitHub repo  (owner/repo/subpath)
skillet add anthropics/skills/skill-creator

# Add all skills from a GitHub repo  (owner/repo)
skillet add wshobson/agents

# Pin to a specific branch or tag  (owner/repo/subpath@ref)
skillet add wshobson/agents/python-design-patterns@main

# Re-sync all sources after editing sources.json
skillet sync

# List installed skills
skillet list

# Remove a skill
skillet remove skill-creator
```

> **Tip:** `skillet.lock` records origins with a `github:` prefix
> (e.g. `github:anthropics/skills/skill-creator`). `skillet add` accepts
> both forms, so you can copy-paste a lock origin directly as a spec.

## Bundled Skills

- `git-os`: Conventional commits, atomic changes, and GIT-OS workflow
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
