import os
import sys
from unittest.mock import patch

sys.path.append(os.getcwd())

from core.repository import resolve_repository


def test_resolve_repository_from_github_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.delenv("UPDATER_REPO_OWNER", raising=False)
    monkeypatch.delenv("UPDATER_REPO_NAME", raising=False)

    owner, repo = resolve_repository()
    assert (owner, repo) == ("owner", "repo")


def test_resolve_repository_from_explicit_env(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setenv("UPDATER_REPO_OWNER", "custom-owner")
    monkeypatch.setenv("UPDATER_REPO_NAME", "custom-repo")

    owner, repo = resolve_repository()
    assert (owner, repo) == ("custom-owner", "custom-repo")


def test_resolve_repository_fallback_defaults(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("UPDATER_REPO_OWNER", raising=False)
    monkeypatch.delenv("UPDATER_REPO_NAME", raising=False)

    with patch("core.repository._resolve_from_git_remote", return_value=None):
        owner, repo = resolve_repository(default_owner="d1", default_repo="d2")

    assert (owner, repo) == ("d1", "d2")
