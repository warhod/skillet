import os
from pathlib import Path

import click

from skillet import __version__
from skillet.config.project import (
    PROJECT_CONFIG_VERSION,
    ensure_project_ide_support,
    get_project_config_dir,
    ide_emit_flags_for_project,
    load_project_config,
    save_project_config,
)
from skillet.config.settings import load_config
from skillet.config.wizard import run_config_wizard
from skillet.installer.copier import copy_all_skills, remove_skill
from skillet.installer.emitters import write_config_files
from skillet.skills.parser import get_skills_from_directory, parse_skill_file
from skillet.skills.search import search_skills
from skillet.sources import (
    apply_all_sources,
    load_sources,
    looks_like_local_source_spec,
    remove_source_entry,
    resolving,
    sources_json_path,
    upsert_source,
)
from skillet.sources.github import (
    GitHubSourceSpec,
    parse_github_source_spec,
    serialize_github_source_spec,
)


def get_bundled_skills_dir() -> Path:
    """Get the path to bundled skills (works both in dev and installed)."""
    package_root = Path(__file__).parent.parent
    bundled = package_root / "skills"
    if bundled.exists():
        return bundled

    src_skills = package_root.parent / "skills"
    if src_skills.exists():
        return src_skills

    raise RuntimeError("Cannot find bundled skills")


def get_project_skills_dir(project_dir: Path) -> Path:
    return project_dir / ".skillet" / "skills"


def _github_token() -> str | None:
    t = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if t:
        return t
    return (load_config().get("github_token") or "").strip() or None


def _parse_local_add_spec(spec: str, project_dir: Path) -> tuple[str, dict] | None:
    """Resolve ``spec`` to a local skill directory; return (skill_name, source_spec)."""
    raw = Path(spec).expanduser()
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw.resolve())
    else:
        candidates.append((project_dir / raw).resolve())
        candidates.append((Path.cwd() / raw).resolve())
    seen: set[Path] = set()
    for src in candidates:
        if src in seen:
            continue
        seen.add(src)
        if src.is_dir() and (src / "SKILL.md").exists():
            name = src.name
            try:
                rel = src.relative_to(project_dir).as_posix()
            except ValueError:
                rel = str(src)
            return name, {"kind": "local", "path": rel}
    return None


@click.group(invoke_without_command=True)
@click.version_option(__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Skillet — install and sync agent skills into your repo"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("install")
@click.argument("directory", default=".")
@click.option(
    "--skip-config",
    is_flag=True,
    help="Skip IDE target prompt and IDE config generation",
)
def install(directory: str, skip_config: bool) -> None:
    """Set up ``.skillet/skills/``, sync sources, prompt for IDE targets once, emit IDE files."""
    project_dir = Path(directory).resolve()
    bundled_skills = get_bundled_skills_dir()
    project_skills = get_project_skills_dir(project_dir)

    click.echo(f"\nInstalling Skillet to: {project_dir}")

    copy_all_skills(bundled_skills, project_skills)
    click.echo("  ✓ Skills copied to .skillet/skills/")

    token = _github_token()
    source_errors = apply_all_sources(
        project_dir, project_skills, github_token=token
    )
    for msg in source_errors:
        click.echo(f"  ! {msg}", err=True)

    get_project_config_dir(project_dir).mkdir(parents=True, exist_ok=True)
    proj_cfg = load_project_config(project_dir)
    proj_cfg.setdefault("version", PROJECT_CONFIG_VERSION)
    if not skip_config:
        ensure_project_ide_support(project_dir)
        proj_cfg = load_project_config(project_dir)
    save_project_config(project_dir, proj_cfg)

    if not skip_config:
        ide_config = ide_emit_flags_for_project(project_dir)
        written = write_config_files(project_skills, project_dir, ide_config)
        for name, path in written.items():
            click.echo(f"  ✓ {name} generated")

    click.echo("\n✓ Installation complete!")


@main.command("add")
@click.argument("spec")
@click.argument("directory", default=".")
def add(spec: str, directory: str) -> None:
    """Add skills from a local directory or GitHub (``owner/repo[/path][@ref]``)."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)
    project_skills.mkdir(parents=True, exist_ok=True)
    token = _github_token()

    parsed = _parse_local_add_spec(spec, project_dir)
    if parsed is not None:
        name, source_spec = parsed
        upsert_source(project_dir, name, source_spec)
        source_errors = apply_all_sources(
            project_dir, project_skills, github_token=token
        )
        for msg in source_errors:
            click.echo(f"  ! {msg}", err=True)
        click.echo(f"✓ Tracked skill '{name}' in .skillet/sources.json")
    elif looks_like_local_source_spec(spec):
        click.echo(
            "Could not find a local skill directory with SKILL.md. "
            "Pass a path relative to the project or an absolute path."
        )
        return
    else:
        try:
            base = parse_github_source_spec(spec.strip())
        except ValueError as e:
            click.echo(str(e))
            return
        try:
            with resolving(spec.strip(), cwd=project_dir, token=token) as resolved:
                dirs = resolved.skill_directories
        except Exception as e:
            click.echo(f"Failed to fetch source: {e}")
            return
        if not dirs:
            click.echo("No skills found in that source.")
            return
        resolved_paths = [d.resolve() for d in dirs]
        try:
            repo_root = Path(os.path.commonpath([str(p) for p in resolved_paths]))
        except ValueError:
            repo_root = dirs[0].parent
        if len(dirs) == 1 and repo_root.resolve() == dirs[0].resolve():
            repo_root = dirs[0].parent

        count = 0
        for d in dirs:
            meta = parse_skill_file(d / "SKILL.md") or {}
            name = str(meta.get("name") or d.name).strip()
            if not name:
                continue
            rel = d.resolve().relative_to(repo_root.resolve()).as_posix()
            sub = rel if rel not in ("", ".") else None
            per = serialize_github_source_spec(
                GitHubSourceSpec(
                    owner=base.owner,
                    repo=base.repo,
                    ref=base.ref,
                    skill_subpath=sub,
                )
            )
            upsert_source(project_dir, name, {"kind": "github", "spec": per})
            count += 1
        if count == 0:
            click.echo("No installable skills found (missing names).")
            return
        click.echo(f"✓ Tracked {count} skill(s) in .skillet/sources.json")
        source_errors = apply_all_sources(
            project_dir, project_skills, github_token=token
        )
        for msg in source_errors:
            click.echo(f"  ! {msg}", err=True)

    ide_config = ide_emit_flags_for_project(project_dir)
    written = write_config_files(project_skills, project_dir, ide_config)
    for fname, _ in written.items():
        click.echo(f"  ✓ {fname} updated")


@main.command("remove")
@click.argument("name")
@click.argument("directory", default=".")
def remove(name: str, directory: str) -> None:
    """Remove an installed skill from ``.skillet/skills/`` and ``sources.json``."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)

    if not project_skills.exists():
        project_skills.mkdir(parents=True, exist_ok=True)

    removed_dir = remove_skill(project_skills, name)
    removed_source = remove_source_entry(project_dir, name)

    if not removed_dir and not removed_source:
        click.echo(f"Skill '{name}' not found")
        return

    click.echo(f"✓ Removed skill '{name}'")

    if project_skills.exists():
        ide_config = ide_emit_flags_for_project(project_dir)
        written = write_config_files(project_skills, project_dir, ide_config)
        for fname, _ in written.items():
            click.echo(f"  ✓ {fname} updated")


@main.command("sync")
@click.argument("directory", default=".")
def sync(directory: str) -> None:
    """Re-fetch sources from ``.skillet/sources.json`` and re-sync IDE configs."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)
    has_sources = sources_json_path(project_dir).exists() and load_sources(project_dir)

    if not project_skills.exists() and not has_sources:
        click.echo("No skills installed. Run 'skillet install' first.")
        return

    project_skills.mkdir(parents=True, exist_ok=True)
    token = _github_token()
    source_errors = apply_all_sources(
        project_dir, project_skills, github_token=token
    )
    for msg in source_errors:
        click.echo(f"  ! {msg}", err=True)

    ide_config = ide_emit_flags_for_project(project_dir)
    written = write_config_files(project_skills, project_dir, ide_config)

    click.echo("\nRe-generated config files:")
    for name, path in written.items():
        click.echo(f"  ✓ {name}")
    click.echo("\n✓ Sync complete!")


@main.command("list")
@click.argument("directory", default=".")
def list_cmd(directory: str) -> None:
    """List installed skills under ``.skillet/skills/``."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)

    if not project_skills.exists():
        click.echo("No skills installed. Run 'skillet install' first.")
        return

    skills = get_skills_from_directory(project_skills)

    if not skills:
        click.echo("No skills found.")
        return

    click.echo(f"\n{'Name':<25} {'Description':<50}")
    click.echo("-" * 75)
    for skill in skills:
        desc = (
            skill["description"][:47] + "..."
            if len(skill["description"]) > 50
            else skill["description"]
        )
        click.echo(f"{skill['name']:<25} {desc:<50}")
    click.echo(f"\n{len(skills)} skill(s)")


@main.command("search")
@click.argument("term")
@click.argument("directory", default=".")
def search_cmd(term: str, directory: str) -> None:
    """Search installed skills by name or description."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)

    if not project_skills.exists():
        click.echo("No skills installed. Run 'skillet install' first.")
        return

    skills = get_skills_from_directory(project_skills)
    results = search_skills(skills, term)

    if not results:
        click.echo(f"No skills found matching '{term}'")
        return

    click.echo(f"\nSearch results for '{term}':\n")
    for skill in results:
        click.echo(f"  {skill['name']} (score: {skill['score']})")
        if skill["description"]:
            click.echo(f"    {skill['description']}")


@main.command("config")
def config_cmd() -> None:
    """Global defaults: IDE targets and optional GitHub token for `skillet add`."""
    run_config_wizard()


if __name__ == "__main__":
    main()
