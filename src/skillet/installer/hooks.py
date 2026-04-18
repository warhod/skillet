from pathlib import Path


POST_COMMIT_HOOK = '''#!/bin/bash
# Skillet - Post-commit hook
# Triggers incremental updates when needed
# Currently a placeholder for future functionality

# Uncomment below to enable auto-analysis:
# skillet analyze --incremental 2>/dev/null || true
'''


def install_git_hook(project_dir: Path, hook_name: str = 'post-commit') -> Path:
    """Install a git hook in the project's .git/hooks directory."""
    hooks_dir = project_dir / '.git' / 'hooks'
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / hook_name
    hook_path.write_text(POST_COMMIT_HOOK, encoding='utf-8')
    hook_path.chmod(0o755)

    return hook_path


def _is_skillet_hook_content(text: str) -> bool:
    return 'Skillet' in text or '# Open Skills - Post-commit' in text


def is_hook_installed(project_dir: Path, hook_name: str = 'post-commit') -> bool:
    """Check if our hook is installed."""
    hook_path = project_dir / '.git' / 'hooks' / hook_name
    if not hook_path.exists():
        return False
    return _is_skillet_hook_content(hook_path.read_text())


def uninstall_git_hook(project_dir: Path, hook_name: str = 'post-commit') -> bool:
    """Remove our git hook."""
    hook_path = project_dir / '.git' / 'hooks' / hook_name
    if hook_path.exists() and _is_skillet_hook_content(hook_path.read_text()):
        hook_path.unlink()
        return True
    return False