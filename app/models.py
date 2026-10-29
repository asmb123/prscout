from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


@dataclass(frozen=True)
class PullRequestContext:
    owner: str
    repository: str
    number: int
    title: str
    body: str
    base_sha: str
    head_sha: str
    head_repository: str
    is_fork: bool


@dataclass(frozen=True)
class ChangedFile:
    path: str
    patch: str
    status: str = "modified"


@dataclass(frozen=True)
class CheckResult:
    command: str
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass(frozen=True)
class Finding:
    title: str
    body: str
    severity: Severity
    path: str | None = None
    line: int | None = None
    side: str = "RIGHT"


@dataclass(frozen=True)
class Review:
    summary: str
    findings: list[Finding] = field(default_factory=list)
    provider: str = "unknown"


@dataclass
class ReviewState:
    pr: PullRequestContext
    files: list[ChangedFile] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    provider: str = ""
    error: str | None = None
    published: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
