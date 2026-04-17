import httpx
import zipfile
import io
from pathlib import Path
from typing import Optional


def fetch_registry(registry_url: str) -> list[dict]:
    """Fetch skills registry from URL."""
    try:
        response = httpx.get(registry_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch registry: {e}")


def download_skill(skill_url: str, dest_dir: Path) -> bool:
    """Download and extract a skill from URL."""
    try:
        response = httpx.get(skill_url, timeout=30)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(dest_dir)
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to download skill: {e}")


def search_registry(registry_url: str, query: str) -> list[dict]:
    """Search the remote registry for skills."""
    registry = fetch_registry(registry_url)
    results = []

    for skill in registry:
        name = skill.get('name', '').lower()
        desc = skill.get('description', '').lower()
        query_lower = query.lower()

        if query_lower in name or query_lower in desc:
            results.append(skill)

    return results