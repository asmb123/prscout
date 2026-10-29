from __future__ import annotations

from typing import Callable

from app.config import ReviewConfig
from app.gith.diff import validate_finding
from app.llm import ReviewProvider
from app.models import ReviewState


def review_pull_request(
    state: ReviewState, config: ReviewConfig, primary: ReviewProvider,
    fallback: ReviewProvider | None = None,
    run_checks: Callable[[ReviewState], list] | None = None,
) -> ReviewState:
    if not state.files:
        state.error = "No changed files were supplied"
        return state
    if run_checks and not state.pr.is_fork:
        state.checks = run_checks(state)
    try:
        review = primary.review(state.files[:config.max_files], state.checks, config.goals)
    except Exception as primary_exc:
        if fallback is None:
            state.error = f"Primary reviewer failed: {primary_exc}"
            return state
        try:
            review = fallback.review(state.files[:config.max_files], state.checks, config.goals)
        except Exception as fallback_exc:
            state.error = (
                f"Primary and fallback reviewers failed. "
                f"Check GROQ_MODEL and GROQ_FALLBACK_MODEL: {fallback_exc}"
            )
            return state
    state.provider = review.provider
    state.summary = review.summary
    state.findings = [f for f in review.findings if validate_finding(f, state.files)]
    state.findings = state.findings[:config.max_comments]
    return state
