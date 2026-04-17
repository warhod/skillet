import click
from pathlib import Path
from open_skills import __version__
from open_skills.skills.parser import get_skills_from_directory
from open_skills.skills.search import search_skills
from open_skills.installer.copier import copy_all_skills, remove_skill
from open_skills.installer.config_gen import write_config_files
from open_skills.installer.hooks import install_git_hook, is_hook_installed
from open_skills.config.wizard import run_config_wizard, load_config
from open_skills.skills.registry import fetch_registry, search_registry, download_skill


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
    return project_dir / '.open-skills' / 'skills'


def get_project_config_dir(project_dir: Path) -> Path:
    """Get the project's config directory."""
    return project_dir / '.open-skills' / 'config'


@click.group()
@click.version_option(__version__)
def main():
    """Open Skills - AI agent skills for developer workflows."""
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

    click.echo(f"\nInstalling Open Skills to: {project_dir}")

    copy_all_skills(bundled_skills, project_skills)
    click.echo(f"  ✓ Skills copied to .open-skills/skills/")

    project_config_dir = get_project_config_dir(project_dir)
    project_config_dir.mkdir(parents=True, exist_ok=True)

    config_path = project_config_dir / 'config.json'
    config_path.write_text('{"version": "1"}', encoding='utf-8')

    if not skip_config:
        config = load_config()
        ide_config = {
            'opencode': 'opencode' in config.get('ide_support', ['opencode']),
            'cursor': 'cursor' in config.get('ide_support', ['cursor']),
            'copilot': 'copilot' in config.get('ide_support', ['copilot']),
        }
        if not any(ide_config.values()):
            ide_config = {'opencode': True, 'cursor': True, 'copilot': True}

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
        click.echo("No skills installed. Run 'open-skills install' first.")
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
        click.echo("No skills installed. Run 'open-skills install' first.")
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
    """Re-sync IDE config files."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)

    if not project_skills.exists():
        click.echo("No skills installed. Run 'open-skills install' first.")
        return

    config = load_config()
    ide_config = {
        'opencode': 'opencode' in config.get('ide_support', ['opencode']),
        'cursor': 'cursor' in config.get('ide_support', ['cursor']),
        'copilot': 'copilot' in config.get('ide_support', ['copilot']),
    }

    written = write_config_files(project_skills, project_dir, ide_config)

    click.echo("\nRe-generated config files:")
    for name, path in written.items():
        click.echo(f"  ✓ {name}")
    click.echo("\n✓ Sync complete!")


@main.command()
@click.argument("name")
@click.argument("directory", default=".")
def add(name, directory):
    """Add a skill from the registry."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)

    config = load_config()
    registry_url = config.get('registry_url')

    if not registry_url:
        click.echo("No registry configured. Run 'open-skills config' first.")
        return

    try:
        results = search_registry(registry_url, name)

        if not results:
            click.echo(f"No skills found in registry matching '{name}'")
            return

        skill = results[0]
        skill_url = skill.get('url')

        if not skill_url:
            click.echo(f"Skill '{name}' found but has no download URL")
            return

        click.echo(f"Downloading '{skill['name']}' from registry...")
        download_skill(skill_url, project_skills)
        click.echo(f"✓ Added skill '{skill['name']}'")

        config = load_config()
        ide_config = {
            'opencode': 'opencode' in config.get('ide_support', ['opencode']),
            'cursor': 'cursor' in config.get('ide_support', ['cursor']),
            'copilot': 'copilot' in config.get('ide_support', ['copilot']),
        }
        written = write_config_files(project_skills, project_dir, ide_config)
        for fname, _ in written.items():
            click.echo(f"  ✓ {fname} updated")

    except Exception as e:
        click.echo(f"Error: {e}")


@main.command()
@click.argument("name")
@click.argument("directory", default=".")
def remove(name, directory):
    """Remove an installed skill."""
    project_dir = Path(directory).resolve()
    project_skills = get_project_skills_dir(project_dir)

    if not project_skills.exists():
        click.echo("No skills installed.")
        return

    if remove_skill(project_skills, name):
        click.echo(f"✓ Removed skill '{name}'")
    else:
        click.echo(f"Skill '{name}' not found")


if __name__ == "__main__":
    main()