- Used **GitHub Actions** to trigger a containerized pipeline on every pull_request event, avoiding the need of a server.

- Used **Docker** to sandbox the execution environment, keeping the agent's runtime decoupled from the target code.

- Used **LangGraph** to orchestrate a stateful, multi-pass PR review workflow and LLM fallback while preserving state.

- Used **PyGithub** to fetch PR diffs, changed files, and commit metadata and post reviews back on the same PR.

- Added a repo-level **.agent-review.md config** to let maintainers customize style rules without touching the core code.

## MVP implementation

The agent is invoked by `.github/workflows/prscout.yml` for opened, synchronized,
and reopened pull requests. It reads the event payload, fetches the pull request
through an injectable PyGithub adapter, runs a compiled LangGraph workflow,
validates inline findings against added diff lines, and publishes one review.

The LangGraph stages are:

```text
run_checks
    ↓
primary_review ── failure ──→ fallback_review
    ↓                         ↓
validate_findings ←───────────┘
    ↓
publish_review
```

Checks are skipped automatically for fork pull requests. The graph is invoked
by the same CLI locally and inside the GitHub Actions container.

Copy `.agent-review.md.example` to `.agent-review.md` to configure goals, limits,
and checks. Configured commands run only for same-repository pull requests;
fork pull requests are diff-only. Never use `pull_request_target` to execute
fork-controlled code with write credentials.

### Local validation

```bash
uv run pytest
uv run prscout --event path/to/pull_request.json
```

The default provider is Groq. Set `GROQ_API_KEY` and optionally `GROQ_MODEL`
(default: `llama-3.3-70b-versatile`). Set `GROQ_FALLBACK_MODEL` to retry with a
second Groq model if the primary model fails.

```bash
export GROQ_API_KEY="your-groq-api-key"
export GROQ_MODEL="llama-3.3-70b-versatile"
export GROQ_FALLBACK_MODEL="openai/gpt-oss-20b"
```

For GitHub Actions, add `GROQ_API_KEY` as an Actions repository secret. Optional
model overrides can be configured as repository Actions variables named
`GROQ_MODEL` and `GROQ_FALLBACK_MODEL`.

## Planned hardening:

1. Inline comment positioning — this is one of the hardest/most impressive parts technically (diff-to-line mapping), don't leave it out if you build it:

```
Implemented diff-to-line position mapping to anchor inline review comments correctly across multi-hunk diffs in the GitHub Reviews API.
```

2. Comment deduplication/state across pushes — shows you thought about real-world repeated triggers, not just a one-shot demo:

```
Used a hidden marker in the PR comment body to detect and update the agent's prior review on synchronize events instead of reposting.
```

3. Security/permissions handling for forks — this is a genuinely valuable line for interviews since most junior projects skip it entirely:

```
Scoped GITHUB_TOKEN permissions and gated pull_request_target usage to safely handle PRs from forked repositories.
```

4. Test/lint integration as agent context — if the container actually runs tests and feeds results into the agent, that's worth its own line, don't fold it into "Docker sandboxing":

```
Fed test and lint output from the CI job as structured context into the review pass to ground suggestions in real failures, not just static diff reading.
```
