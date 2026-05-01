# Releasing Agent Skillet

This runbook documents the release process for publishing `agent-skillet` to PyPI.

## Version: single source of truth

The **only** version you maintain by hand is **`version` in `pyproject.toml`** (`[project]`). The build copies that into wheel/sdist **package metadata**, and PyPI indexes that value.

At runtime, `skillet.__version__` (and thus `skillet --version`, `agent-skillet --version`, and the GitHub `User-Agent` string) is read with **`importlib.metadata.version("agent-skillet")`**, which returns whatever metadata was installed—so it always matches the shipped package. If the importable package is not installed (rare; e.g. bare `PYTHONPATH` without a install), the code falls back to `0.0.0+unknown`.

**Bump checklist:** edit `pyproject.toml` → run `uv lock` → commit → tag **`v`**`X.Y.Z` matching that version (see `release.yml` guard) → publish the GitHub Release. Do not reintroduce a hardcoded `__version__` string in `src/skillet/__init__.py`; it would drift from PyPI.

## When to create the tag

**Tag only after the release commit is on `main`**, not on a feature or PR branch.

- A tag should point at the exact commit that shipped the version bump (the one consumers get from `main`).
- If you tag on a PR branch, the tag may point at a commit that never becomes `main`, or at a squash merge’s parent instead of the merge commit—releases and `release.yml` then won’t match what people actually merged.
- Typical flow: open a PR with the version bump → merge to `main` → `git checkout main && git pull` → create and push the tag on that tip of `main`.

## Preconditions

- You have push access to `main` and can create tags.
- GitHub Actions is enabled for this repository.
- PyPI Trusted Publisher is configured for this repo/workflow (`publish.yml`).
- Local branch is up to date and CI is passing.

## Release flow going forward

```bash
# 1. Bump version in pyproject.toml, merge to main (via PR), then:
git checkout main
git pull origin main

# 2. Create and push a tag (on main, after the version bump is merged)
git tag v0.1.0
git push origin v0.1.0

# 3. On GitHub: Releases -> open auto-created draft release for that tag -> Publish release
#    -> publish.yml triggers automatically
```

## What happens in CI/CD

- Tag push (`v*`) triggers `.github/workflows/release.yml`.
- `release.yml` builds artifacts and creates a **draft** GitHub Release with `dist/*`.
- Publishing that draft release triggers `.github/workflows/publish.yml`.
- `publish.yml` builds again and publishes to PyPI via `pypa/gh-action-pypi-publish`.

## File layout after changes

```text
.github/
  workflows/
    ci.yml
    publish.yml
    release.yml
pyproject.toml      # distribution name is "agent-skillet"
```

## Install docs to update in README (after publish)

```bash
uvx agent-skillet init            # one-off run; needs script name = package name (0.1.1+)
uv tool install agent-skillet     # global; installs `skillet` and `agent-skillet` on PATH
```

## Troubleshooting

- **Release workflow failed: “Tagged commit … is not on origin/main” (or your default branch)**
  - The tag points at a commit that is not in default-branch history. Merge the release to `main`, move or delete the bad tag, and tag again from `main`.

- **Tag/version mismatch in release workflow**
  - `release.yml` enforces `tag == v<project.version>`.
  - Fix either the tag or `pyproject.toml` version so they match.

- **Publish workflow did not run**
  - Ensure you clicked **Publish release** (saving draft is not enough).
  - Ensure release is not marked prerelease; `publish.yml` skips prereleases.

- **PyPI publish auth error**
  - Recheck PyPI Trusted Publisher mapping:
    - Owner/org
    - Repo name
    - Workflow filename `publish.yml`
