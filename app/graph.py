from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import ReviewConfig
from app.execution import run_command
from app.gith.client import GitHubClient
from app.gith.diff import validate_finding
from app.llm import ReviewProvider
from app.models import CheckResult, ChangedFile, Finding, PullRequestContext, ReviewState


class ReviewGraphState(TypedDict, total=False):
    pr: PullRequestContext
    files: list[ChangedFile]
    checks: list[CheckResult]
    findings: list[Finding]
    summary: str
    provider: str
    error: str | None
    primary_error: str | None
    published: bool


def _run_configured_checks(state: ReviewGraphState, config: ReviewConfig, cwd: str) -> dict:
    pr = state["pr"]
    if pr.is_fork:
        return {"checks": []}
    checks = [
        run_command(command, cwd=Path(cwd))
        for command in config.commands
    ]
    return {"checks": checks}


def build_review_graph(
    config: ReviewConfig,
    primary: ReviewProvider,
    fallback: ReviewProvider | None = None,
    github: GitHubClient | None = None,
    working_directory: str = ".",
) -> object:
    """Build the executable LangGraph review workflow."""

    def run_checks_node(state: ReviewGraphState) -> dict:
        return _run_configured_checks(state, config, working_directory)

    def primary_node(state: ReviewGraphState) -> dict:
        try:
            review = primary.review(
                state["files"][:config.max_files],
                state.get("checks", []),
                config.goals,
            )
            return {
                "summary": review.summary,
                "findings": review.findings,
                "provider": review.provider,
                "primary_error": None,
            }
        except Exception as exc:
            if fallback is None:
                return {"error": f"Primary reviewer failed: {exc}"}
            return {"primary_error": str(exc)}

    def fallback_node(state: ReviewGraphState) -> dict:
        if fallback is None:
            return {"error": "Primary reviewer failed and no fallback is configured"}
        try:
            review = fallback.review(
                state["files"][:config.max_files],
                state.get("checks", []),
                config.goals,
            )
            return {
                "summary": review.summary,
                "findings": review.findings,
                "provider": review.provider,
                "primary_error": None,
            }
        except Exception as exc:
            return {
                "error": (
                    "Primary and fallback reviewers failed. "
                    f"Check GROQ_MODEL and GROQ_FALLBACK_MODEL: {exc}"
                )
            }

    def validate_node(state: ReviewGraphState) -> dict:
        findings = [
            finding
            for finding in state.get("findings", [])
            if validate_finding(finding, state["files"])
        ]
        return {"findings": findings[:config.max_comments]}

    def publish_node(state: ReviewGraphState) -> dict:
        if github is None:
            return {"published": False}
        try:
            github.publish_review(
                state["pr"],
                state.get("summary", "No summary provided."),
                state.get("findings", []),
            )
            return {"published": True}
        except Exception as exc:
            return {"error": f"Failed to publish GitHub review: {exc}"}

    def after_primary(state: ReviewGraphState) -> str:
        if state.get("error"):
            return "end"
        if state.get("primary_error"):
            return "fallback"
        return "validate"

    def after_validate(state: ReviewGraphState) -> str:
        return "end" if state.get("error") else "publish"

    workflow = StateGraph(ReviewGraphState)
    workflow.add_node("run_checks", run_checks_node)
    workflow.add_node("primary_review", primary_node)
    workflow.add_node("fallback_review", fallback_node)
    workflow.add_node("validate_findings", validate_node)
    workflow.add_node("publish_review", publish_node)
    workflow.add_edge(START, "run_checks")
    workflow.add_edge("run_checks", "primary_review")
    workflow.add_conditional_edges(
        "primary_review",
        after_primary,
        {"fallback": "fallback_review", "validate": "validate_findings", "end": END},
    )
    workflow.add_edge("fallback_review", "validate_findings")
    workflow.add_conditional_edges(
        "validate_findings",
        after_validate,
        {"publish": "publish_review", "end": END},
    )
    workflow.add_edge("publish_review", END)
    return workflow.compile()


def review_pull_request(
    state: ReviewState,
    config: ReviewConfig,
    primary: ReviewProvider,
    fallback: ReviewProvider | None = None,
) -> ReviewState:
    """Compatibility wrapper for callers that do not publish reviews."""
    graph = build_review_graph(config, primary, fallback)
    result = graph.invoke(
        {
            "pr": state.pr,
            "files": state.files,
            "checks": state.checks,
            "findings": state.findings,
        }
    )
    state.checks = result.get("checks", [])
    state.findings = result.get("findings", [])
    state.summary = result.get("summary", "")
    state.provider = result.get("provider", "")
    state.error = result.get("error")
    return state
