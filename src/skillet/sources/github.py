"""GitHub tarball fetch + skills.sh-style source specs (owner/repo, paths, @ref)."""

from __future__ import annotations

import io
import re
import shutil
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from skillet import __version__

_OWNER_REPO_PART = re.compile(r"^[^/\s@]+$")


@dataclass(frozen=True)
class GitHubSourceSpec:
    owner: str
    repo: str
    ref: str | None
    """None means default branch (try main, then master)."""
    skill_subpath: str | None
    """Directory path inside the repo root for a single skill, or None for all skills."""


def _split_spec_and_ref(spec: str) -> tuple[str, str | None]:
    """Split ``owner/repo/...@ref`` into path part and optional ref."""
    s = spec.strip()
    if "@" not in s:
        return s, None
    left, ref = s.rsplit("@", 1)
    ref = ref.strip()
    if not ref:
        msg = f"Invalid ref in source spec: {spec!r}"
        raise ValueError(msg)
    return left, ref


def _validate_owner_repo(owner: str, repo: str, spec: str) -> None:
    """Validate owner/repo tokens in a GitHub source spec."""
    for label, value in (("owner", owner), ("repo", repo)):
        if not _OWNER_REPO_PART.match(value):
            msg = f"Invalid GitHub {label} in source spec: {spec!r}"
            raise ValueError(msg)


def parse_github_source_spec(spec: str) -> GitHubSourceSpec:
    """Parse a GitHub source string. Caller should ensure this is not a local path spec."""
    s = spec.strip()
    if not s or "/" not in s:
        msg = f"Invalid GitHub source spec (expected owner/repo): {spec!r}"
        raise ValueError(msg)

    left, ref = _split_spec_and_ref(s)

    parts = [p for p in left.strip().split("/") if p]
    if len(parts) < 2:
        msg = f"Invalid GitHub source spec (expected owner/repo): {spec!r}"
        raise ValueError(msg)

    owner, repo = parts[0], parts[1]
    _validate_owner_repo(owner, repo, spec)

    skill_subpath = "/".join(parts[2:]) if len(parts) > 2 else None
    if skill_subpath == "":
        skill_subpath = None

    return GitHubSourceSpec(
        owner=owner,
        repo=repo,
        ref=ref,
        skill_subpath=skill_subpath,
    )


def serialize_github_source_spec(source: GitHubSourceSpec) -> str:
    """Serialize a parsed spec back to a ``skills.sh``-style string for source storage."""
    s = f"{source.owner}/{source.repo}"
    if source.skill_subpath:
        s += f"/{source.skill_subpath}"
    if source.ref:
        s += f"@{source.ref}"
    return s


def _tarball_url_candidates(owner: str, repo: str, ref: str) -> list[str]:
    o = quote(owner, safe="")
    r = quote(repo, safe="")
    rq = quote(ref, safe="")
    return [
        f"https://codeload.github.com/{o}/{r}/tar.gz/{rq}",
        f"https://codeload.github.com/{o}/{r}/tar.gz/refs/heads/{rq}",
        f"https://codeload.github.com/{o}/{r}/tar.gz/refs/tags/{rq}",
    ]


def _request_headers(token: str | None) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/octet-stream",
        "User-Agent": f"skillet/{__version__}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _download_first_available(
    owner: str,
    repo: str,
    ref: str,
    *,
    token: str | None,
    client: httpx.Client,
) -> bytes:
    last: httpx.HTTPStatusError | None = None
    headers = _request_headers(token)
    for url in _tarball_url_candidates(owner, repo, ref):
        r = client.get(url, headers=headers)
        try:
            r.raise_for_status()
            return r.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                last = e
                continue
            raise
    if last is not None:
        raise last
    msg = f"No tarball matched for {owner}/{repo}@{ref}"
    raise RuntimeError(msg)


def discover_skill_directories(repo_root: Path) -> list[Path]:
    """Return every directory under repo_root that directly contains SKILL.md."""
    found: list[Path] = []
    for skill_md in repo_root.rglob("SKILL.md"):
        if any(p.startswith(".") for p in skill_md.parts):
            continue
        found.append(skill_md.parent)
    return sorted(found, key=lambda p: str(p.relative_to(repo_root)))


def _is_within_root(path: Path, root: Path) -> bool:
    """Whether ``path`` is contained by ``root``."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _skill_subpath_candidates(repo_root: Path, skill_subpath: str) -> list[Path]:
    """Candidate skill directories for a subpath selector."""
    direct = (repo_root / skill_subpath).resolve()
    candidates: list[Path] = [direct]
    if "/" not in skill_subpath:
        # skills.sh repos often store named skills under these roots.
        candidates.extend(
            [
                (repo_root / "skills" / skill_subpath).resolve(),
                (repo_root / ".agents" / "skills" / skill_subpath).resolve(),
                (repo_root / ".claude" / "skills" / skill_subpath).resolve(),
            ]
        )
    return candidates


def _select_skill_directories(
    repo_root: Path,
    skill_subpath: str | None,
) -> list[Path]:
    if skill_subpath is None:
        dirs = discover_skill_directories(repo_root)
        if not dirs:
            msg = f"No SKILL.md found under extracted repo root {repo_root}"
            raise ValueError(msg)
        return dirs
    root = repo_root.resolve()
    candidates = _skill_subpath_candidates(repo_root, skill_subpath)

    for target in candidates:
        if not _is_within_root(target, root):
            continue
        if (target / "SKILL.md").is_file():
            return [target]

    # Last fallback: treat a single-segment path as a skill name selector.
    if "/" not in skill_subpath:
        want = skill_subpath.strip()
        matches: list[Path] = []
        for d in discover_skill_directories(repo_root):
            if d.name == want:
                matches.append(d)
        if len(matches) == 1:
            return matches
        if len(matches) > 1:
            msg = f"Ambiguous skill name {skill_subpath!r}; matched multiple SKILL.md dirs"
            raise ValueError(msg)

    msg = f"No SKILL.md at expected path(s) for {skill_subpath!r}"
    raise ValueError(msg)


def _extract_strip_topdir(archive: bytes, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        tf.extractall(dest, filter="data")
    entries = list(dest.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest


def _refs_to_try(source: GitHubSourceSpec) -> list[str]:
    """Return refs to try in priority order for tarball download."""
    if source.ref is not None:
        return [source.ref]
    return ["main", "master"]


def _download_archive_for_source(
    source: GitHubSourceSpec,
    *,
    token: str | None,
    client: httpx.Client,
) -> bytes:
    refs_order = _refs_to_try(source)
    archive: bytes | None = None
    last: Exception | None = None
    for ref in refs_order:
        try:
            archive = _download_first_available(
                source.owner, source.repo, ref, token=token, client=client
            )
            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 and source.ref is None:
                last = e
                continue
            raise
    if archive is not None:
        return archive
    msg = (
        f"Could not download {source.owner}/{source.repo}"
        + (f"@{source.ref}" if source.ref else " (tried main, master)")
    )
    raise RuntimeError(msg) from last


def fetch_github_skill_directories(
    source: GitHubSourceSpec,
    *,
    token: str | None = None,
    client: httpx.Client | None = None,
) -> tuple[list[Path], Callable[[], None]]:
    """
    Download and extract the repo tarball, returning absolute skill directory paths.

    The returned cleanup callback removes the temporary extraction directory.
    """
    own_client = client is None
    http = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        archive = _download_archive_for_source(source, token=token, client=http)
    finally:
        if own_client:
            http.close()

    tmp = tempfile.mkdtemp(prefix="skillet-gh-")

    def cleanup() -> None:
        shutil.rmtree(tmp, ignore_errors=True)

    try:
        repo_root = _extract_strip_topdir(archive, Path(tmp))
        dirs = _select_skill_directories(repo_root, source.skill_subpath)
        return dirs, cleanup
    except Exception:
        cleanup()
        raise
