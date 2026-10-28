"""Thin client for GitHub's REST API, used by the research totals. The repo
is public, so no login is needed. GITHUB_TOKEN (optional) only raises the
rate limit from 60 to 5000 requests an hour."""

import os

import requests

API_URL = "https://api.github.com"


def _get_all(path, params=None):
    """Every item from a paginated list endpoint, following GitHub's `Link`
    headers."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = API_URL + path
    params = {"per_page": 100, **(params or {})}
    items = []
    while url:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        items += response.json()
        url = response.links.get("next", {}).get("url")
        params = None  # the "next" link already carries them
    return items


def get_issues(repo):
    """All issues, open and closed. GitHub's issues list includes pull
    requests too (they have a "pull_request" key)."""
    return _get_all(f"/repos/{repo}/issues", {"state": "all"})


def get_pulls(repo):
    """All pull requests, open and closed."""
    return _get_all(f"/repos/{repo}/pulls", {"state": "all"})


def get_commits(repo):
    """All commits on the default branch."""
    return _get_all(f"/repos/{repo}/commits")
