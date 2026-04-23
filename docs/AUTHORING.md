# Authoring skills for Skillet

Skills are directories that contain a `SKILL.md` file. The file starts with **YAML frontmatter** (between `---` lines) followed by Markdown instructions for coding agents.

## Required frontmatter

| Field | Meaning |
|-------|---------|
| `name` | Stable id (lowercase, hyphens). Defaults to the parent directory name if omitted. |
| `description` | One-line summary; used in `skillet list` and search. |

## Example

```markdown
---
name: my-skill
description: When editing payment code, follow these invariants.
---

# My skill

## When to use
- Any change under `src/payments/`

## Steps
1. Read existing tests under `tests/payments/`.
2. …
```

## Where skills live

- **Skills** defaults live in this repository at `skills/` and are copied to `.skillet/skills/` on `skillet install`.
- **Repo-owned** skills live anywhere in your tree (e.g. `./team-skills/checkout-flow/`). Register them with:

  ```bash
  skillet add ./team-skills/checkout-flow
  ```

- **Upstream** skills use GitHub specs compatible with [skills.sh](https://skills.sh/), e.g. `anthropics/skills/skill-creator` or `owner/repo/path/to/skill-dir@branch`.

## Install source selection (`.skillet/config/sources.json`)

`skillet install` and `skillet sync` read `.skillet/config/sources.json` as the single source of truth.

- `kind: "local"` with `"source": "<name>"` resolves to `./skills/<name>/`
- `kind: "local"` with `"path": "<dir>"` resolves directly to that directory
- `kind: "github"` uses the same spec format as `skillet add`

Example: install only local `git-os` (exclude other repo skills):

```json
{
  "git-os": {
    "kind": "local",
    "source": "git-os"
  }
}
```

## Where agents load skills (native paths)

On `skillet install`, `skillet sync`, and `skillet add`, Skillet **mirrors** each materialized skill from `.skillet/skills/<name>/` into the enabled targets’ native trees (one `SKILL.md` per skill folder):

| Target | Project path |
|--------|----------------|
| Claude Code (`claude` in `ide_support`) | `.claude/skills/<name>/SKILL.md` |
| Cursor (`cursor`) | `.cursor/skills/<name>/SKILL.md` |
| OpenCode / universal agents (`opencode`) | `.agents/skills/<name>/SKILL.md` |

The `gemini` key in `ide_support` is reserved for future use; in the current version Skillet does **not** write files for it. Use `opencode` if you need `.agents/skills/`.

## Agent Skills specification

For broader compatibility across tools, see [agentskills.io](https://agentskills.io).
