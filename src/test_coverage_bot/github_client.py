from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from .config import Config
from .constants import COMMENT_MARKER
from .http_client import JsonHttpClient
from .issue_parser import IssueParser
from .models import Issue


class GitHubClient:
    def __init__(self, http_client: JsonHttpClient, issue_parser: IssueParser) -> None:
        self.http_client = http_client
        self.issue_parser = issue_parser

    def fetch_labeled_issues(self, config: Config) -> list[Issue]:
        query = urlencode({"state": "open", "labels": config.label, "per_page": "100"})
        repo_path = quote(config.repository, safe="/")
        url = f"{config.github_api_base_url.rstrip('/')}/repos/{repo_path}/issues?{query}"
        raw_issues = self.http_client.request("GET", url, self.headers(config))
        if not isinstance(raw_issues, list):
            raise RuntimeError("GitHub issues response was not a JSON array")

        issues: list[Issue] = []
        for raw_issue in raw_issues:
            if not isinstance(raw_issue, dict):
                continue
            issue = self.issue_parser.parse_issue(raw_issue, config.repository)
            if issue and config.label in issue.labels:
                issues.append(issue)
        return issues

    def post_issue_comment(self, config: Config, issue: Issue, body: str) -> dict[str, Any]:
        if config.dry_run:
            return {"dry_run": True, "would_comment": body}
        if not config.github_token:
            return {"skipped": True, "reason": "GITHUB_TOKEN not set"}

        repo_path = quote(issue.repository, safe="/")
        url = f"{config.github_api_base_url.rstrip('/')}/repos/{repo_path}/issues/{issue.number}/comments"
        headers = self.headers(config)
        headers["Content-Type"] = "application/json"
        return self.http_client.request("POST", url, headers, {"body": body})

    def has_processed_comment(self, config: Config, issue: Issue) -> bool:
        if not config.github_token:
            return False

        repo_path = quote(issue.repository, safe="/")
        url = (
            f"{config.github_api_base_url.rstrip('/')}"
            f"/repos/{repo_path}/issues/{issue.number}/comments?per_page=100"
        )
        comments = self.http_client.request("GET", url, self.headers(config))
        if not isinstance(comments, list):
            return False

        for comment in comments:
            if isinstance(comment, dict) and COMMENT_MARKER in str(comment.get("body") or ""):
                return True
        return False

    def headers(self, config: Config) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "test-coverage-bot",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if config.github_token:
            headers["Authorization"] = f"Bearer {config.github_token}"
        return headers
