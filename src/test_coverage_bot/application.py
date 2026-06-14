from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Config
from .devin_client import DevinClient
from .github_client import GitHubClient
from .issue_parser import IssueParser
from .models import Issue
from .prompting import DevinPromptBuilder, IssueCommentBuilder
from .storage import EventLogger, OutputWriter, StateStore
from .time_utils import utc_now


class TestCoverageBot:
    def __init__(
        self,
        github_client: GitHubClient,
        devin_client: DevinClient,
        issue_parser: IssueParser,
        prompt_builder: DevinPromptBuilder,
        comment_builder: IssueCommentBuilder,
        state_store: StateStore,
        output_writer: OutputWriter,
        event_logger: EventLogger,
    ) -> None:
        self.github_client = github_client
        self.devin_client = devin_client
        self.issue_parser = issue_parser
        self.prompt_builder = prompt_builder
        self.comment_builder = comment_builder
        self.state_store = state_store
        self.output_writer = output_writer
        self.event_logger = event_logger

    def poll_once(self, config: Config, fixture: Path | None) -> int:
        self.event_logger.append(
            config.output_dir,
            "poll_started",
            {"label": config.label, "repository": config.repository, "fixture": str(fixture) if fixture else None},
        )
        issues = self.load_issues(config, fixture)
        processed_count = self.process_issues(config, issues)
        self.event_logger.append(config.output_dir, "run_completed", {"processed_count": processed_count})
        print(f"Processed {processed_count} new issue(s)")
        return processed_count

    def load_issues(self, config: Config, fixture: Path | None) -> list[Issue]:
        if fixture:
            return self.issue_parser.parse_fixture(fixture, config.repository, config.label)
        return self.github_client.fetch_labeled_issues(config)

    def process_issues(self, config: Config, issues: list[Issue]) -> int:
        state = self.state_store.load(config.state_file)
        processed = state.get("processed", {})
        results: list[dict[str, Any]] = []

        self.event_logger.append(config.output_dir, "poll_completed", {"issue_count": len(issues)})
        for issue in issues:
            if self.should_skip_issue(config, issue, processed):
                continue
            results.append(self.process_issue(config, issue))

        self.output_writer.write(config.output_dir, results)
        return len(results)

    def should_skip_issue(self, config: Config, issue: Issue, processed: dict[str, Any]) -> bool:
        if issue.identifier in processed:
            self.event_logger.append(config.output_dir, "skipped_processed", {"issue": issue.identifier})
            return True
        if not config.dry_run and self.github_client.has_processed_comment(config, issue):
            self.state_store.mark_processed(config.state_file, issue, "existing issue comment")
            self.event_logger.append(config.output_dir, "skipped_existing_comment", {"issue": issue.identifier})
            return True
        return False

    def process_issue(self, config: Config, issue: Issue) -> dict[str, Any]:
        prompt = self.prompt_builder.build(issue, config.label)
        response = self.devin_client.create_session(config, prompt)
        session = self.devin_client.session_reference(response)
        comment = self.comment_builder.build(issue, session, bool(response.get("dry_run")))
        comment_response = self.github_client.post_issue_comment(config, issue, comment)

        result = {
            "timestamp": utc_now(),
            "issue": self.output_writer.issue_to_dict(issue),
            "devin_response": response,
            "github_comment_response": comment_response,
        }
        if not config.dry_run:
            self.state_store.mark_processed(config.state_file, issue, session)

        self.event_logger.append(
            config.output_dir,
            "session_created" if not response.get("dry_run") else "session_dry_run",
            {"issue": issue.identifier, "session": session, "github_comment": comment_response},
        )
        print(f"Processed {issue.identifier}: {session}")
        return result
