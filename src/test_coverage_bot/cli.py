from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .application import TestCoverageBot
from .config import ConfigFactory
from .devin_client import DevinClient
from .env import DotEnvLoader
from .github_client import GitHubClient
from .http_client import JsonHttpClient
from .issue_parser import IssueParser
from .prompting import CoverageFormatter, DevinPromptBuilder, IssueCommentBuilder
from .storage import EventLogger, OutputWriter, StateStore


class Cli:
    def run(self) -> int:
        args = self.build_parser().parse_args()
        DotEnvLoader().load(args.env_file)
        config = ConfigFactory().from_args(args)
        if args.fixture and not args.dry_run:
            print("--fixture is intended for --dry-run simulation", file=sys.stderr)
            return 2

        bot = self.create_bot()
        cycle_count = 0
        while True:
            bot.poll_once(config, args.fixture)
            cycle_count += 1
            if args.once or (args.max_cycles is not None and cycle_count >= args.max_cycles):
                return 0
            print(f"Sleeping {config.interval_seconds} seconds before the next poll")
            time.sleep(config.interval_seconds)

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Poll GitHub issues and create Devin test-coverage sessions")
        parser.add_argument("--repo", help="GitHub repository, for example apache/superset")
        parser.add_argument("--label", help="Issue label to poll for")
        parser.add_argument(
            "--interval",
            type=int,
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
        return parser

    def create_bot(self) -> TestCoverageBot:
        http_client = JsonHttpClient()
        issue_parser = IssueParser()
        coverage_formatter = CoverageFormatter()
        devin_client = DevinClient(http_client)
        return TestCoverageBot(
            github_client=GitHubClient(http_client, issue_parser),
            devin_client=devin_client,
            issue_parser=issue_parser,
            prompt_builder=DevinPromptBuilder(coverage_formatter),
            comment_builder=IssueCommentBuilder(coverage_formatter),
            state_store=StateStore(),
            output_writer=OutputWriter(devin_client),
            event_logger=EventLogger(),
        )


def main() -> int:
    return Cli().run()
