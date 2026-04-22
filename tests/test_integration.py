from pathlib import Path

from skillet.installer.copier import copy_all_skills, remove_skill
from skillet.installer.emitters import write_config_files
from skillet.skills.parser import parse_skill_file
from skillet.skills.search import search_skills


def test_parse_skill_file():
    from skillet.cli import get_bundled_skills_dir
    bundled = get_bundled_skills_dir()
    git_os_skill = bundled / 'git-os' / 'SKILL.md'
    skill = parse_skill_file(git_os_skill)
    assert skill is not None
    assert skill['name'] == 'git-os'
    assert 'description' in skill


def test_parse_skill_file_not_exists():
    skill = parse_skill_file(Path('/nonexistent/SKILL.md'))
    assert skill is None


def test_search_skills():
    skills = [
        {'name': 'git-os', 'description': 'Conventional commits'},
        {'name': 'sprint', 'description': 'Ticket automation'},
    ]
    results = search_skills(skills, 'git commit')
    assert len(results) >= 1
    assert any(r['name'] == 'git-os' for r in results)


def test_search_skills_exact_match():
    skills = [
        {'name': 'git-os', 'description': 'Conventional commits'},
    ]
    results = search_skills(skills, 'git-os')
    assert len(results) == 1
    assert results[0]['name'] == 'git-os'


def test_copy_and_remove_skill(tmp_path):
    from skillet.cli import get_bundled_skills_dir
    
    # Copy skills
    dest = tmp_path / 'skills'
    count = copy_all_skills(get_bundled_skills_dir(), dest)
    assert count == 3
    assert (dest / 'git-os' / 'SKILL.md').exists()
    
    # Remove a skill
    removed = remove_skill(dest, 'git-os')
    assert removed is True
    assert not (dest / 'git-os').exists()
    
    # Remove non-existent returns False
    removed = remove_skill(dest, 'nonexistent')
    assert removed is False


def test_copy_emit_remove_prunes_all_native_mirrors(tmp_path: Path) -> None:
    """Bundled skills copied to the store, mirrored natively, then removed everywhere."""
    from skillet.cli import get_bundled_skills_dir

    project_skills = tmp_path / ".skillet" / "skills"
    count = copy_all_skills(get_bundled_skills_dir(), project_skills)
    assert count >= 1

    flags = {"claude": True, "cursor": True, "opencode": True}
    write_config_files(project_skills, tmp_path, flags)

    assert (tmp_path / ".claude/skills/git-os/SKILL.md").is_file()
    assert (tmp_path / ".cursor/skills/git-os/SKILL.md").is_file()
    assert (tmp_path / ".agents/skills/git-os/SKILL.md").is_file()

    assert remove_skill(project_skills, "git-os") is True
    write_config_files(project_skills, tmp_path, flags)

    for base in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert not (tmp_path / base / "git-os").exists()

    assert not (tmp_path / ".cursor/rules/skillet.mdc").exists()