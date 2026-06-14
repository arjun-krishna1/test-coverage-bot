from __future__ import annotations

from .constants import COMMENT_MARKER
from .models import Issue


class CoverageFormatter:
    def summary(self, issue: Issue) -> str:
        if not issue.coverage:
            return "Coverage before: not provided\nCoverage after: pending Devin run"

        lines = ["Coverage before:"]
        for metric in issue.coverage:
            count = ""
            if metric.covered and metric.total:
                count = f" ({metric.covered} / {metric.total})"
            lines.append(f"- {metric.name}: {metric.percent}{count}")
        lines.append("Coverage after: pending Devin run")
        return "\n".join(lines)


class DevinPromptBuilder:
    def __init__(self, coverage_formatter: CoverageFormatter) -> None:
        self.coverage_formatter = coverage_formatter

    def build(self, issue: Issue, label: str) -> str:
        file_line = f"\nTarget file: {issue.file_path}" if issue.file_path else ""
        coverage = self.coverage_formatter.summary(issue)
        return f"""You are responding to a polling test coverage automation that turns labeled GitHub issues into production-quality pull requests.

Repository: {issue.repository}
Polling label: {label}
Issue: {issue.identifier}
Issue URL: {issue.html_url}
Title: {issue.title}{file_line}

{coverage}

Issue context:
{issue.description}

Please inspect the repository and create a focused pull request that remediates this issue.

Expected workflow:
1. Read the issue context and identify the code path that needs coverage.
2. Find nearby existing tests and follow the repository's established test style.
3. Add the smallest high-signal tests that cover the acceptance criteria without broad refactors.
4. Run the most relevant test command and any targeted coverage command you can identify.
5. Open a pull request with a clear title, concise summary, tests run, coverage before, coverage after when available, and a link back to the issue.
6. After the pull request is opened, post a follow-up comment on the source GitHub issue with the PR link, coverage after, tests run, and any remaining limitations.
7. If a pull request cannot be opened, leave a concise technical status update explaining the blocker and the exact next step.

Required follow-up issue comment:
- Post it on this source issue: {issue.html_url}
- Start with: "## Coverage improvement automation completed"
- Include: pull request URL, summary of test coverage added, commands run, coverage before, coverage after, and any caveats.
- If exact updated coverage is unavailable, include the best available evidence from the tests or coverage command and explain what prevented exact measurement.
- Do not leave the source issue with only the initial "automation started" comment.

Quality bar:
- Prefer deterministic unit or component tests over brittle end-to-end tests unless the issue explicitly requires browser coverage.
- Mock network, browser, filesystem, clock, and external service boundaries when possible.
- Do not make unrelated refactors, dependency changes, formatting sweeps, or product behavior changes.
- If the issue includes acceptance criteria, cover each criterion or explain why one cannot be covered.
- Include the exact commands you ran and the observed result in the pull request description.

Optimize for a reviewable, low-risk PR that a senior engineer would be comfortable merging."""


class IssueCommentBuilder:
    def __init__(self, coverage_formatter: CoverageFormatter) -> None:
        self.coverage_formatter = coverage_formatter

    def build(self, issue: Issue, session: str, dry_run: bool) -> str:
        status = "dry-run" if dry_run else "created"
        return f"""{COMMENT_MARKER}

## Coverage improvement automation started

- **Status:** Devin session {status}
- **Devin session:** {session}
- **Target:** {issue.file_path or 'not specified'}

{self.coverage_formatter.summary(issue)}

The polling bot asked Devin to create a focused test-coverage pull request, run the relevant tests, and return to this issue with a follow-up comment that includes the PR link, updated coverage, tests run, and any caveats."""
