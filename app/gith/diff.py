from __future__ import annotations

import re

from app.models import ChangedFile, Finding

HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_lines(file: ChangedFile) -> set[int]:
    lines: set[int] = set()
    new_line = 0
    for raw in file.patch.splitlines():
        match = HUNK_RE.match(raw)
        if match:
            new_line = int(match.group(1))
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            lines.add(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith(" ") or raw == "":
            new_line += 1
    return lines


def validate_finding(finding: Finding, files: list[ChangedFile]) -> bool:
    if not finding.path or finding.line is None:
        return True
    file = next((item for item in files if item.path == finding.path), None)
    return file is not None and finding.line in changed_lines(file)
