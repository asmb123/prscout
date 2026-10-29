from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(ValueError):
    """Raised when repository or environment configuration is invalid."""


@dataclass(frozen=True)
class CommandConfig:
    command: str
    timeout_seconds: int = 120


@dataclass(frozen=True)
class ReviewConfig:
    goals: list[str] = field(default_factory=lambda: ["Correctness", "Security", "Maintainability"])
    include: list[str] = field(default_factory=lambda: ["**/*"])
    exclude: list[str] = field(default_factory=list)
    commands: list[CommandConfig] = field(default_factory=list)
    max_files: int = 100
    max_diff_bytes: int = 200_000
    max_findings: int = 20
    max_comments: int = 10
    checks_blocking: bool = False


def parse_agent_review(text: str) -> ReviewConfig:
    values: dict[str, str] = {}
    commands: list[CommandConfig] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ConfigurationError(f"Invalid configuration line: {raw_line}")
        key, value = (part.strip() for part in line.split(":", 1))
        if key == "command":
            parts = shlex.split(value)
            if not parts or len(parts) > 2:
                raise ConfigurationError("command must be quoted, with optional timeout")
            timeout = int(parts[1]) if len(parts) == 2 else 120
            commands.append(CommandConfig(parts[0], timeout))
        else:
            values[key] = value

    def csv(key: str, default: list[str]) -> list[str]:
        value = values.get(key)
        return [item.strip() for item in value.split(",") if item.strip()] if value else default

    def bounded_int(key: str, default: int, maximum: int) -> int:
        try:
            value = int(values.get(key, default))
        except ValueError as exc:
            raise ConfigurationError(f"{key} must be an integer") from exc
        if value < 1 or value > maximum:
            raise ConfigurationError(f"{key} must be between 1 and {maximum}")
        return value

    return ReviewConfig(
        goals=csv("goals", ["Correctness", "Security", "Maintainability"]),
        include=csv("include", ["**/*"]),
        exclude=csv("exclude", []),
        commands=commands,
        max_files=bounded_int("max_files", 100, 1000),
        max_diff_bytes=bounded_int("max_diff_bytes", 200_000, 2_000_000),
        max_findings=bounded_int("max_findings", 20, 100),
        max_comments=bounded_int("max_comments", 10, 50),
        checks_blocking=values.get("checks_blocking", "false").lower() == "true",
    )


def load_review_config(root: Path) -> ReviewConfig:
    path = root / ".agent-review.md"
    return parse_agent_review(path.read_text(encoding="utf-8")) if path.exists() else ReviewConfig()


def github_token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("ACCESS_TOKEN")
    if not token:
        raise ConfigurationError("GITHUB_TOKEN is required")
    return token
