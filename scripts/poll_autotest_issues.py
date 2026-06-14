"""Poll GitHub issues and create Devin test-coverage remediation sessions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_DEVIN_API_BASE_URL = "https://api.devin.ai/v3"
DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"
DEFAULT_LABEL = "autotest"
DEFAULT_INTERVAL_SECONDS = 600
COMMENT_MARKER = "<!-- test-coverage-bot:processed -->"


@dataclass(frozen=True)
class CoverageMetric:
    name: str
    percent: str
    covered: str | None = None
    total: str | None = None


@dataclass(frozen=True)
class Issue:
    identifier: str
    title: str
    description: str
    repository: str
    number: int
    html_url: str
    file_path: str | None = None
    labels: tuple[str, ...] = ()
    coverage: tuple[CoverageMetric, ...] = ()


@dataclass(frozen=True)
class Config:
    repository: str
    label: str
    interval_seconds: int
    output_dir: Path
    state_file: Path
    dry_run: bool
    devin_api_key: str | None
    devin_org_id: str | None
    devin_create_as_user_id: str | None
    devin_api_base_url: str
    github_token: str | None
    github_api_base_url: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def read_json(path: Path) -> Any:
    with path.open() as input_file:
        return json.load(input_file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def append_log(output_dir: Path, event: str, details: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": utc_now(), "event": event, **details}
    with (output_dir / "events.jsonl").open("a") as log_file:
        log_file.write(json.dumps(record, sort_keys=True) + "\n")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"processed": {}}
    state = read_json(path)
    if not isinstance(state, dict):
        return {"processed": {}}
    if not isinstance(state.get("processed"), dict):
        state["processed"] = {}
    return state


def mark_processed(path: Path, issue: Issue, session: str) -> None:
    state = load_state(path)
    state.setdefault("processed", {})[issue.identifier] = {
        "processed_at": utc_now(),
        "title": issue.title,
        "url": issue.html_url,
        "devin_session": session,
    }
    write_json(path, state)


def coverage_metrics_from_text(text: str) -> tuple[CoverageMetric, ...]:
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


def file_from_text(text: str) -> str | None:
    match = re.search(r"-\s*File:\s*`([^`]+)`", text)
    return match.group(1) if match else None


def labels_from_issue(raw_issue: dict[str, Any]) -> tuple[str, ...]:
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


def parse_issue(raw_issue: dict[str, Any], repository: str) -> Issue | None:
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
        html_url=str(
            raw_issue.get("html_url") or f"https://github.com/{repository}/issues/{number}"
        ),
        file_path=file_from_text(body),
        labels=labels_from_issue(raw_issue),
        coverage=coverage_metrics_from_text(body),
    )


def parse_fixture(path: Path, repository: str, label: str) -> list[Issue]:
    payload = read_json(path)
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
        issue = parse_issue(raw_issue, repository)
        if issue and label in issue.labels:
            issues.append(issue)
    return issues


def http_json_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method, headers=headers)

    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310
            raw_response = response.read().decode("utf-8")
    except HTTPError as ex:
        error_body = ex.read().decode("utf-8")
        raise RuntimeError(f"HTTP {ex.code} from {url}: {error_body}") from ex
    except URLError as ex:
        raise RuntimeError(f"Unable to reach {url}: {ex.reason}") from ex

    return json.loads(raw_response) if raw_response else {}


def github_headers(config: Config) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "test-coverage-bot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if config.github_token:
        headers["Authorization"] = f"Bearer {config.github_token}"
    return headers


def fetch_labeled_issues(config: Config) -> list[Issue]:
    query = urlencode({"state": "open", "labels": config.label, "per_page": "100"})
    repo_path = quote(config.repository, safe="/")
    url = f"{config.github_api_base_url.rstrip('/')}/repos/{repo_path}/issues?{query}"
    raw_issues = http_json_request("GET", url, github_headers(config))
    if not isinstance(raw_issues, list):
        raise RuntimeError("GitHub issues response was not a JSON array")

    issues: list[Issue] = []
    for raw_issue in raw_issues:
        if not isinstance(raw_issue, dict):
            continue
        issue = parse_issue(raw_issue, config.repository)
        if issue and config.label in issue.labels:
            issues.append(issue)
    return issues


def coverage_summary(issue: Issue) -> str:
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


def build_prompt(issue: Issue, label: str) -> str:
    file_line = f"\nTarget file: {issue.file_path}" if issue.file_path else ""
    return f"""You are responding to a polling test coverage automation that turns labeled GitHub issues into production-quality pull requests.

Repository: {issue.repository}
Polling label: {label}
Issue: {issue.identifier}
Issue URL: {issue.html_url}
Title: {issue.title}{file_line}

{coverage_summary(issue)}

Issue context:
{issue.description}

Please inspect the repository and create a focused pull request that remediates this issue.

Expected workflow:
1. Read the issue context and identify the code path that needs coverage.
2. Find nearby existing tests and follow the repository's established test style.
3. Add the smallest high-signal tests that cover the acceptance criteria without broad refactors.
4. Run the most relevant test command and any targeted coverage command you can identify.
5. Open a pull request with a clear title, concise summary, tests run, coverage before, coverage after when available, and a link back to the issue.
6. If a pull request cannot be opened, leave a concise technical status update explaining the blocker and the exact next step.

Quality bar:
- Prefer deterministic unit or component tests over brittle end-to-end tests unless the issue explicitly requires browser coverage.
- Mock network, browser, filesystem, clock, and external service boundaries when possible.
- Do not make unrelated refactors, dependency changes, formatting sweeps, or product behavior changes.
- If the issue includes acceptance criteria, cover each criterion or explain why one cannot be covered.
- Include the exact commands you ran and the observed result in the pull request description.

Optimize for a reviewable, low-risk PR that a senior engineer would be comfortable merging."""


def create_devin_session(config: Config, prompt: str) -> dict[str, Any]:
    body: dict[str, Any] = {"prompt": prompt}
    if config.devin_create_as_user_id:
        body["create_as_user_id"] = config.devin_create_as_user_id

    if config.dry_run:
        return {"dry_run": True, "request_body": body}

    if not config.devin_api_key or not config.devin_org_id:
        raise RuntimeError("DEVIN_API_KEY and DEVIN_ORG_ID are required for live runs")

    url = (
        f"{config.devin_api_base_url.rstrip('/')}"
        f"/organizations/{config.devin_org_id}/sessions"
    )
    return http_json_request(
        "POST",
        url,
        {"Authorization": f"Bearer {config.devin_api_key}", "Content-Type": "application/json"},
        body,
    )


def devin_session_reference(response: dict[str, Any]) -> str:
    return str(
        response.get("url")
        or response.get("session_url")
        or response.get("session_id")
        or response.get("id")
        or "dry-run"
    )


def issue_comment_body(issue: Issue, response: dict[str, Any]) -> str:
    session = devin_session_reference(response)
    status = "dry-run" if response.get("dry_run") else "created"
    return f"""{COMMENT_MARKER}

## Autotest automation started

- **Status:** Devin session {status}
- **Devin session:** {session}
- **Target:** {issue.file_path or 'not specified'}

{coverage_summary(issue)}

The polling bot asked Devin to create a focused test-coverage pull request, run the relevant tests, and report coverage before and after when available."""


def post_issue_comment(config: Config, issue: Issue, body: str) -> dict[str, Any]:
    if config.dry_run:
        return {"dry_run": True, "would_comment": body}
    if not config.github_token:
        return {"skipped": True, "reason": "GITHUB_TOKEN not set"}

    repo_path = quote(issue.repository, safe="/")
    url = f"{config.github_api_base_url.rstrip('/')}/repos/{repo_path}/issues/{issue.number}/comments"
    headers = github_headers(config)
    headers["Content-Type"] = "application/json"
    return http_json_request("POST", url, headers, {"body": body})


def issue_has_processed_comment(config: Config, issue: Issue) -> bool:
    if not config.github_token:
        return False

    repo_path = quote(issue.repository, safe="/")
    url = (
        f"{config.github_api_base_url.rstrip('/')}"
        f"/repos/{repo_path}/issues/{issue.number}/comments?per_page=100"
    )
    comments = http_json_request("GET", url, github_headers(config))
    if not isinstance(comments, list):
        return False

    for comment in comments:
        if isinstance(comment, dict) and COMMENT_MARKER in str(comment.get("body") or ""):
            return True
    return False


def build_report(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Test Coverage Bot Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "| Issue | Target | Devin session | Status | Coverage before | Coverage after |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        issue = result["issue"]
        response = result["devin_response"]
        status = "dry-run" if response.get("dry_run") else "created"
        coverage = issue.get("coverage") or []
        before = ", ".join(f"{metric['name']} {metric['percent']}" for metric in coverage)
        lines.append(
            f"| {issue['identifier']} | {issue.get('file_path') or 'n/a'} | "
            f"{devin_session_reference(response)} | {status} | "
            f"{before or 'not provided'} | pending |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_dir: Path, results: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "devin-remediation-results.json", results)
    (output_dir / "devin-remediation-report.md").write_text(build_report(results))


def process_issues(config: Config, issues: list[Issue]) -> int:
    state = load_state(config.state_file)
    processed = state.get("processed", {})
    results: list[dict[str, Any]] = []

    append_log(config.output_dir, "poll_completed", {"issue_count": len(issues)})
    for issue in issues:
        if issue.identifier in processed:
            append_log(config.output_dir, "skipped_processed", {"issue": issue.identifier})
            continue
        if not config.dry_run and issue_has_processed_comment(config, issue):
            mark_processed(config.state_file, issue, "existing issue comment")
            append_log(
                config.output_dir,
                "skipped_existing_comment",
                {"issue": issue.identifier},
            )
            continue

        response = create_devin_session(config, build_prompt(issue, config.label))
        comment_response = post_issue_comment(config, issue, issue_comment_body(issue, response))
        session = devin_session_reference(response)
        results.append(
            {
                "timestamp": utc_now(),
                "issue": {**asdict(issue), "coverage": [asdict(metric) for metric in issue.coverage]},
                "devin_response": response,
                "github_comment_response": comment_response,
            }
        )

        if not config.dry_run:
            mark_processed(config.state_file, issue, session)

        append_log(
            config.output_dir,
            "session_created" if not response.get("dry_run") else "session_dry_run",
            {"issue": issue.identifier, "session": session, "github_comment": comment_response},
        )
        print(f"Processed {issue.identifier}: {session}")

    write_outputs(config.output_dir, results)
    return len(results)


def build_config(args: argparse.Namespace) -> Config:
    repository = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        raise ValueError("Repository is required. Set --repo or GITHUB_REPOSITORY.")

    return Config(
        repository=repository,
        label=args.label,
        interval_seconds=args.interval,
        output_dir=args.output_dir,
        state_file=args.state_file,
        dry_run=args.dry_run,
        devin_api_key=os.environ.get("DEVIN_API_KEY"),
        devin_org_id=os.environ.get("DEVIN_ORG_ID"),
        devin_create_as_user_id=os.environ.get("DEVIN_CREATE_AS_USER_ID"),
        devin_api_base_url=os.environ.get("DEVIN_API_BASE_URL", DEFAULT_DEVIN_API_BASE_URL),
        github_token=os.environ.get("GITHUB_TOKEN"),
        github_api_base_url=os.environ.get("GITHUB_API_BASE_URL", DEFAULT_GITHUB_API_BASE_URL),
    )


def poll_once(config: Config, fixture: Path | None) -> int:
    append_log(
        config.output_dir,
        "poll_started",
        {"label": config.label, "repository": config.repository, "fixture": str(fixture) if fixture else None},
    )
    issues = parse_fixture(fixture, config.repository, config.label) if fixture else fetch_labeled_issues(config)
    processed_count = process_issues(config, issues)
    append_log(config.output_dir, "run_completed", {"processed_count": processed_count})
    print(f"Processed {processed_count} new issue(s)")
    return processed_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll GitHub issues labeled autotest and create Devin sessions")
    parser.add_argument("--repo", help="GitHub repository, for example apache/superset")
    parser.add_argument("--label", default=os.environ.get("AUTOTEST_LABEL", DEFAULT_LABEL), help="Issue label to poll for")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("POLL_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)),
        help="Polling interval in seconds",
    )
    parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit")
    parser.add_argument(
        "--max-cycles",
        type=int,
        help="Maximum number of poll cycles before exiting; useful for bounded workflow runs",
    )
    parser.add_argument("--fixture", type=Path, help="Local GitHub issues fixture for dry-run simulation")
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"), help="Optional local env file")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Observability output directory")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("outputs/processed-issues.json"),
        help="JSON state file used to avoid duplicate Devin sessions",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not call Devin or post GitHub comments")
    args = parser.parse_args()

    load_dotenv(args.env_file)
    config = build_config(args)
    if args.fixture and not args.dry_run:
        print("--fixture is intended for --dry-run simulation", file=sys.stderr)
        return 2

    cycle_count = 0
    while True:
        poll_once(config, args.fixture)
        cycle_count += 1
        if args.once or (args.max_cycles is not None and cycle_count >= args.max_cycles):
            return 0
        print(f"Sleeping {config.interval_seconds} seconds before the next poll")
        time.sleep(config.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
