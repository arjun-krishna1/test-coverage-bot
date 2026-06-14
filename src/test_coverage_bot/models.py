from __future__ import annotations

from dataclasses import dataclass


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
