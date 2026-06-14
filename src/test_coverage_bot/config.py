from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    DEFAULT_DEVIN_API_BASE_URL,
    DEFAULT_GITHUB_API_BASE_URL,
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_LABEL,
)


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


class ConfigFactory:
    def from_args(self, args: argparse.Namespace) -> Config:
        repository = args.repo or os.environ.get("GITHUB_REPOSITORY")
        if not repository:
            raise ValueError("Repository is required. Set --repo or GITHUB_REPOSITORY.")

        return Config(
            repository=repository,
            label=args.label or os.environ.get("AUTOTEST_LABEL", DEFAULT_LABEL),
            interval_seconds=args.interval
            if args.interval is not None
            else int(os.environ.get("POLL_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)),
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
