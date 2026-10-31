from app.config import parse_agent_review
from app.gith.diff import changed_lines, validate_finding
from app.models import ChangedFile, Finding, Severity


def test_config_parser_bounds_and_commands():
    config = parse_agent_review("goals: Security, Correctness\ncommand: ruff 30\nmax_comments: 3")
    assert config.goals == ["Security", "Correctness"]
    assert config.commands[0].timeout_seconds == 30
    assert config.max_comments == 3


def test_diff_mapping_only_accepts_added_lines():
    file = ChangedFile("app.py", "@@ -1,2 +1,3 @@\n old\n+new\n context")
    assert changed_lines(file) == {2}
    assert validate_finding(Finding("x", "y", Severity.high, "app.py", 2), [file])
    assert not validate_finding(Finding("x", "y", Severity.high, "app.py", 1), [file])
