from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from open_skills.skills.parser import get_skills_from_directory, generate_skills_xml


def get_templates_dir() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent.parent / 'templates'


def generate_claude_md(skills: list[dict], base_dir: Path) -> str:
    """Generate CLAUDE.md content."""
    env = Environment(
        loader=FileSystemLoader(str(get_templates_dir())),
        autoescape=select_autoescape(['html', 'xml']),
    )
    template = env.get_template('claude.md.j2')
    skills_xml = generate_skills_xml(skills, base_dir)
    return template.render(skills_xml=skills_xml)


def generate_cursorrules(skills: list[dict], base_dir: Path) -> str:
    """Generate .cursorrules content."""
    env = Environment(
        loader=FileSystemLoader(str(get_templates_dir())),
        autoescape=select_autoescape(['html', 'xml']),
    )
    template = env.get_template('cursorrules.j2')
    skills_xml = generate_skills_xml(skills, base_dir)
    return template.render(skills_xml=skills_xml)


def generate_copilot_md(skills: list[dict], base_dir: Path) -> str:
    """Generate .github/copilot-instructions.md content."""
    env = Environment(
        loader=FileSystemLoader(str(get_templates_dir())),
        autoescape=select_autoescape(['html', 'xml']),
    )
    template = env.get_template('copilot.md.j2')
    skills_xml = generate_skills_xml(skills, base_dir)
    return template.render(skills_xml=skills_xml)


def write_config_files(skills_dir: Path, project_dir: Path, config: dict) -> dict:
    """Write all IDE config files. Returns dict of written files."""
    skills = get_skills_from_directory(skills_dir)
    result = {}

    if config.get('opencode') or config.get('claude'):
        content = generate_claude_md(skills, project_dir)
        claude_path = project_dir / 'CLAUDE.md'
        claude_path.write_text(content, encoding='utf-8')
        result['CLAUDE.md'] = str(claude_path)

    if config.get('cursor'):
        content = generate_cursorrules(skills, project_dir)
        cursor_path = project_dir / '.cursorrules'
        cursor_path.write_text(content, encoding='utf-8')
        result['.cursorrules'] = str(cursor_path)

    if config.get('copilot'):
        copilot_dir = project_dir / '.github'
        copilot_dir.mkdir(exist_ok=True)
        content = generate_copilot_md(skills, project_dir)
        copilot_path = copilot_dir / 'copilot-instructions.md'
        copilot_path.write_text(content, encoding='utf-8')
        result['.github/copilot-instructions.md'] = str(copilot_path)

    return result