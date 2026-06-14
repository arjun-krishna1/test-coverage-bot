from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import CoverageMetric, Issue


class IssueParser:
    def coverage_metrics_from_text(self, text: str) -> tuple[CoverageMetric, ...]:
        metrics: list[CoverageMetric] = []
        pattern = re.compile(
            r"-\s*(Lines|Branches|Functions):\s*\*\*([^*]+)\*\*"
            r"(?:\s*\(`?([^`/]+)\s*/\s*([^`)]+)`?\))?",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            metrics.append(
                CoverageMetric(
                    name=match.group(1).lower(),
                    percent=match.group(2).strip(),
                    covered=match.group(3).strip() if match.group(3) else None,
                    total=match.group(4).strip() if match.group(4) else None,
                )
            )
        return tuple(metrics)

    def parse_issue(self, raw_issue: dict[str, Any], repository: str) -> Issue | None:
        if "pull_request" in raw_issue:
            return None

        number = raw_issue.get("number")
        if not isinstance(number, int):
            return None

        body = str(raw_issue.get("body") or "")
        return Issue(
            identifier=f"{repository}#{number}",
            title=str(raw_issue.get("title") or f"Issue {number}"),
            description=body or "No issue body provided.",
            repository=repository,
            number=number,
            html_url=str(raw_issue.get("html_url") or f"https://github.com/{repository}/issues/{number}"),
            file_path=self.file_from_text(body),
            labels=self.labels_from_issue(raw_issue),
            coverage=self.coverage_metrics_from_text(body),
        )

    def parse_fixture(self, path: Path, repository: str, label: str) -> list[Issue]:
        payload = json.loads(path.read_text())
        if isinstance(payload, dict):
            repository = str(payload.get("repository") or repository)
            raw_issues = payload.get("issues", [])
        else:
            raw_issues = payload

        if not isinstance(raw_issues, list):
            raise ValueError("Fixture must be a JSON array or an object with an issues array")

        issues: list[Issue] = []
        for raw_issue in raw_issues:
            if not isinstance(raw_issue, dict):
                continue
            issue = self.parse_issue(raw_issue, repository)
            if issue and label in issue.labels:
                issues.append(issue)
        return issues

    def file_from_text(self, text: str) -> str | None:
        match = re.search(r"-\s*File:\s*`([^`]+)`", text)
        return match.group(1) if match else None

    def labels_from_issue(self, raw_issue: dict[str, Any]) -> tuple[str, ...]:
        labels = raw_issue.get("labels", [])
        if not isinstance(labels, list):
            return ()

        names: list[str] = []
        for label in labels:
            if isinstance(label, dict) and label.get("name"):
                names.append(str(label["name"]))
            elif isinstance(label, str):
                names.append(label)
        return tuple(names)
