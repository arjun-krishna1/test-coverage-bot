from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .devin_client import DevinClient
from .models import Issue
from .time_utils import utc_now


class EventLogger:
    def append(self, output_dir: Path, event: str, details: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": utc_now(), "event": event, **details}
        with (output_dir / "events.jsonl").open("a") as log_file:
            log_file.write(json.dumps(record, sort_keys=True) + "\n")


class StateStore:
    def load(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"processed": {}}
        state = json.loads(path.read_text())
        if not isinstance(state, dict):
            return {"processed": {}}
        if not isinstance(state.get("processed"), dict):
            state["processed"] = {}
        return state

    def mark_processed(self, path: Path, issue: Issue, session: str) -> None:
        state = self.load(path)
        state.setdefault("processed", {})[issue.identifier] = {
            "processed_at": utc_now(),
            "title": issue.title,
            "url": issue.html_url,
            "devin_session": session,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True))


class OutputWriter:
    def __init__(self, devin_client: DevinClient) -> None:
        self.devin_client = devin_client

    def write(self, output_dir: Path, results: list[dict[str, Any]]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        self.write_json(output_dir / "devin-remediation-results.json", results)
        (output_dir / "devin-remediation-report.md").write_text(self.build_report(results))

    def issue_to_dict(self, issue: Issue) -> dict[str, Any]:
        return {**asdict(issue), "coverage": [asdict(metric) for metric in issue.coverage]}

    def build_report(self, results: list[dict[str, Any]]) -> str:
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
                f"{self.devin_client.session_reference(response)} | {status} | "
                f"{before or 'not provided'} | pending |"
            )
        lines.append("")
        return "\n".join(lines)

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True))
