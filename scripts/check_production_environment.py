#!/usr/bin/env python3
"""Fail unless the GitHub production environment enforces owner review."""

from __future__ import annotations

import json
import os
import sys
import urllib.request


def main() -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    expected_reviewer = os.environ["EXPECTED_PRODUCTION_REVIEWER"]
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/environments/production",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ajha-info-deploy/1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        environment = json.load(response)
    reviewer_rules = [
        rule for rule in environment.get("protection_rules", [])
        if rule.get("type") == "required_reviewers" and rule.get("reviewers")
    ]
    if not reviewer_rules:
        raise SystemExit("production environment has no enforced required reviewers")
    reviewer_entries = [
        reviewer
        for rule in reviewer_rules
        for reviewer in rule.get("reviewers", [])
    ]
    if len(reviewer_entries) != 1:
        raise SystemExit("production environment must require only the designated owner reviewer")
    reviewer = reviewer_entries[0]
    if reviewer.get("type") != "User" or reviewer.get("reviewer", {}).get("login") != expected_reviewer:
        raise SystemExit(f"production environment does not exclusively require owner {expected_reviewer}")
    prevents_self_review = any(rule.get("prevent_self_review") is True for rule in reviewer_rules)
    print(
        "production environment requires owner reviewer "
        f"{expected_reviewer}; prevent_self_review={str(prevents_self_review).lower()}"
    )


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, json.JSONDecodeError) as error:
        print(f"environment verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
