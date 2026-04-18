import pytest
from pathlib import Path
from skillet.skills.parser import parse_frontmatter, get_skills_from_directory


def test_parse_frontmatter():
    content = """---
name: test-skill
description: A test skill
metadata:
  author: test
  version: "1.0"
---

# Skill Content
"""
    result = parse_frontmatter(content)
    assert result['name'] == 'test-skill'
    assert result['description'] == 'A test skill'


def test_parse_frontmatter_empty():
    content = "No frontmatter here"
    result = parse_frontmatter(content)
    assert result == {}


def test_get_skills_from_directory():
    from skillet.cli import get_bundled_skills_dir
    bundled = get_bundled_skills_dir()
    skills = get_skills_from_directory(bundled)
    assert len(skills) >= 3
    names = [s['name'] for s in skills]
    assert 'git-os' in names