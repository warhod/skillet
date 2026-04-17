from pathlib import Path
import questionary
from questionary import prompt


def get_config_path() -> Path:
    """Get the global config path."""
    config_dir = Path.home() / '.config' / 'open-skills'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.json'


def load_config() -> dict:
    """Load configuration from global config file."""
    config_path = get_config_path()
    if config_path.exists():
        import json
        return json.loads(config_path.read_text())
    return {
        'registry_url': '',
        'openrouter_api_key': '',
        'anthropic_api_key': '',
        'github_token': '',
        'ide_support': ['opencode', 'cursor', 'copilot'],
    }


def save_config(config: dict) -> None:
    """Save configuration to global config file."""
    import json
    config_path = get_config_path()
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def run_config_wizard() -> None:
    """Run interactive configuration wizard."""
    config = load_config()

    questions = [
        {
            'type': 'input',
            'name': 'registry_url',
            'message': 'Registry URL (press Enter for default):',
            'default': config.get('registry_url', 'https://raw.githubusercontent.com/open-skills/registry/main/index.json'),
        },
        {
            'type': 'input',
            'name': 'openrouter_api_key',
            'message': 'OpenRouter API Key (press Enter to skip):',
            'default': config.get('openrouter_api_key', ''),
        },
        {
            'type': 'input',
            'name': 'anthropic_api_key',
            'message': 'Anthropic API Key (press Enter to skip):',
            'default': config.get('anthropic_api_key', ''),
        },
        {
            'type': 'input',
            'name': 'github_token',
            'message': 'GitHub Token (press Enter to skip):',
            'default': config.get('github_token', ''),
        },
    ]

    answers = prompt(questions)

    config.update({
        'registry_url': answers['registry_url'],
        'openrouter_api_key': answers['openrouter_api_key'],
        'anthropic_api_key': answers['anthropic_api_key'],
        'github_token': answers['github_token'],
    })

    save_config(config)

    print("\n✓ Configuration saved to ~/.config/open-skills/config.json")
    print("\nTo use in your project, add to your .env file:")
    print(f"  OPEN_SKILLS_REGISTRY_URL={config['registry_url']}")
    if config['openrouter_api_key']:
        print("  OPENROUTER_API_KEY=...")
    if config['anthropic_api_key']:
        print("  ANTHROPIC_API_KEY=...")
    if config['github_token']:
        print("  GITHUB_TOKEN=...")


def ensure_project_env(project_dir: Path) -> None:
    """Ensure project has .env file with open-skills config."""
    env_path = project_dir / '.env'
    global_config = load_config()

    lines = []
    if env_path.exists():
        lines = env_path.read_text().split('\n')

    existing_keys = {line.split('=')[0] for line in lines if '=' in line}

    if 'OPEN_SKILLS_REGISTRY_URL' not in existing_keys and global_config.get('registry_url'):
        lines.append(f'OPEN_SKILLS_REGISTRY_URL={global_config["registry_url"]}')

    env_path.write_text('\n'.join(lines), encoding='utf-8')