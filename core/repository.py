"""
Repository resolution helpers shared by updater-related modules.
"""

from __future__ import annotations

import os
import re
import subprocess


_GITHUB_HTTPS_RE = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")


def _parse_repo_from_origin(origin_url: str) -> tuple[str, str] | None:
    if not origin_url:
        return None

    origin = origin_url.strip()
    match = _GITHUB_HTTPS_RE.search(origin)
    if not match:
        return None

    return match.group("owner"), match.group("repo")


def _resolve_from_git_remote() -> tuple[str, str] | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return None

    return _parse_repo_from_origin(result.stdout)


def resolve_repository(
    default_owner: str = "cfopuser",
    default_repo: str = "app-store",
) -> tuple[str, str]:
    """
    Resolve GitHub owner/repo in a deterministic order:
    1) GITHUB_REPOSITORY (CI)
    2) UPDATER_REPO_OWNER + UPDATER_REPO_NAME
    3) git remote.origin.url
    4) provided defaults
    """
    github_repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if github_repo and "/" in github_repo:
        owner, repo = github_repo.split("/", 1)
        if owner and repo:
            return owner, repo

    owner = os.getenv("UPDATER_REPO_OWNER", "").strip()
    repo = os.getenv("UPDATER_REPO_NAME", "").strip()
    if owner and repo:
        return owner, repo

    from_git = _resolve_from_git_remote()
    if from_git:
        return from_git

    return default_owner, default_repo
