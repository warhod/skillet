import click
from pathlib import Path
from skillet import __version__
from skillet.skills.parser import get_skills_from_directory
from skillet.skills.search import search_skills
from skillet.installer.copier import copy_all_skills, remove_skill
from skillet.installer.config_gen import write_config_files
from skillet.installer.hooks import install_git_hook, is_hook_installed
from skillet.config.wizard import run_config_wizard, load_config
from skillet.sources import (
    apply_all_sources,
    load_sources,
    remove_source_entry,
    sources_json_path,
    upsert_source,
)


def get_bundled_skills_dir() -> Path:
    """Get the path to bundled skills (works both in dev and installed)."""
    # First try: package root
    package_root = Path(__file__).parent.parent
    bundled = package_root / 'skills'
    if bundled.exists():
        return bundled
    
    # Second try: src/skills (when using src layout)
    src_skills = package_root.parent / 'skills'
    if src_skills.exists():
        return src_skills
    
    raise RuntimeError("Cannot find bundled skills")


def get_project_skills_dir(project_dir: Path) -> Path:
    """Get the project's skills directory."""
    return project_dir / '.skillet' / 'skills'


def get_project_config_dir(project_dir: Path) -> Path:
    """Get the project's config directory."""
    return project_dir / '.skillet' / 'config'


def _ide_config_from_global() -> dict:
    config = load_config()
    default_ides = ['claude', 'cursor', 'opencode', 'gemini']
    ide_config = {
        'claude': 'claude' in config.get('ide_support', default_ides),
        'cursor': 'cursor' in config.get('ide_support', default_ides),
        'opencode': 'opencode' in config.get('ide_support', default_ides),
        'gemini': 'gemini' in config.get('ide_support', default_ides),
    }
    if not any(ide_config.values()):
        ide_config = {k: True for k in ide_config}
    return ide_config


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
        if src.is_dir() and (src / 'SKILL.md').exists():
            name = src.name
            try:
                rel = src.relative_to(project_dir).as_posix()
            except ValueError:
                rel = str(src)
            return name, {'kind': 'local', 'path': rel}
    return None


@click.group()
@click.version_option(__version__)
def main():
    """Skillet — prepare and serve agent skills into your repo."""
    pass


@main.command()
@click.argument("directory", default=".")
@click.option("--skip-config", is_flag=True, help="Skip IDE config generation")
@click.option("--all", is_flag=True, help="Install all available skills")
@click.option("--with-hooks", is_flag=True, help="Install git hooks")
def install(directory, skip_config, all, with_hooks):
    """Install skills into a project directory."""
    project_dir = Path(directory).resolve()
    bundled_skills = get_bundled_skills_dir()
    project_skills = get_project_skills_dir(project_dir)

    click.echo(f"\nInstalling Skillet to: {project_dir}")

    copy_all_skills(bundled_skills, project_skills)
    click.echo(f"  ✓ Skills copied to .skillet/skills/")

    source_errors = apply_all_sources(project_dir, project_skills)
    for msg in source_errors:
        click.echo(f"  ! {msg}", err=True)

    project_config_dir = get_project_config_dir(project_dir)
    project_config_dir.mkdir(parents=True, exist_ok=True)

    config_path = project_config_dir / 'config.json'
    config_path.write_text('{"version": "1"}', encoding='utf-8')

    if not skip_config:
        ide_config = _ide_config_from_global()
        written = write_config_files(project_skills, project_dir, ide_config)
        for name, path in written.items():
            click.echo(f"  ✓ {name} generated")

    if with_hooks:
        hook_path = install_git_hook(project_dir)
        click.echo(f"  ✓ Git hook installed: {hook_path}")

    click.echo("\n✓ Installation complete!")


@main.command()
@click.argument("directory", default=".")
def list(directory):
    """List installed skills."""
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
        desc = skill['description'][:47] + '...' if len(skill['description']) > 50 else skill['description']
        click.echo(f"{skill['name']:<25} {desc:<50}")
    click.echo(f"\n{len(skills)} skill(s)")


@main.command()
@click.argument("term")
@click.argument("directory", default=".")
def search(term, directory):
    """Search skills by name or description."""
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
        if skill['description']:
            click.echo(f"    {skill['description']}")


@main.command()
def config():
    """Configure API keys and settings."""
    run_config_wizard()


@main.command()
@click.argument("directory", default=".")
def sync(directory):
    """Re-fetch sources from ``.skillet/sources.json`` and re-sync IDE configs."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)
    has_sources = sources_json_path(project_dir).exists() and load_sources(project_dir)

    if not project_skills.exists() and not has_sources:
        click.echo("No skills installed. Run 'skillet install' first.")
        return

    project_skills.mkdir(parents=True, exist_ok=True)
    source_errors = apply_all_sources(project_dir, project_skills)
    for msg in source_errors:
        click.echo(f"  ! {msg}", err=True)

    ide_config = _ide_config_from_global()
    written = write_config_files(project_skills, project_dir, ide_config)

    click.echo("\nRe-generated config files:")
    for name, path in written.items():
        click.echo(f"  ✓ {name}")
    click.echo("\n✓ Sync complete!")


@main.command()
@click.argument("spec")
@click.argument("directory", default=".")
def add(spec, directory):
    """Add a skill from a local directory (``owner/repo`` support is planned)."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)
    project_skills.mkdir(parents=True, exist_ok=True)

    parsed = _parse_local_add_spec(spec, project_dir)
    if parsed is None:
        click.echo(
            "Could not find a local skill directory with SKILL.md. "
            "Pass a path relative to the project or an absolute path."
        )
        return

    name, source_spec = parsed
    upsert_source(project_dir, name, source_spec)
    source_errors = apply_all_sources(project_dir, project_skills)
    for msg in source_errors:
        click.echo(f"  ! {msg}", err=True)

    click.echo(f"✓ Tracked skill '{name}' in .skillet/sources.json")

    ide_config = _ide_config_from_global()
    written = write_config_files(project_skills, project_dir, ide_config)
    for fname, _ in written.items():
        click.echo(f"  ✓ {fname} updated")


@main.command()
@click.argument("name")
@click.argument("directory", default=".")
def remove(name, directory):
    """Remove an installed skill."""
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
        ide_config = _ide_config_from_global()
        written = write_config_files(project_skills, project_dir, ide_config)
        for fname, _ in written.items():
            click.echo(f"  ✓ {fname} updated")


if __name__ == "__main__":
    main()