from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from github import Auth, Github

from app.models import ChangedFile, Finding, PullRequestContext


class GitHubClient(Protocol):
    def get_pull_request(self, owner: str, repository: str, number: int) -> PullRequestContext: ...
    def get_changed_files(self, pr: PullRequestContext) -> list[ChangedFile]: ...
    def publish_review(self, pr: PullRequestContext, summary: str, findings: list[Finding]) -> None: ...


@dataclass
class PyGithubClient:
    token: str

    def __post_init__(self) -> None:
        self._github = Github(auth=Auth.Token(self.token))

    def get_pull_request(self, owner: str, repository: str, number: int) -> PullRequestContext:
        pull = self._github.get_repo(f"{owner}/{repository}").get_pull(number)
        head_repo = pull.head.repo.full_name if pull.head.repo else f"{owner}/{repository}"
        return PullRequestContext(
            owner, repository, number, pull.title, pull.body or "", pull.base.sha,
            pull.head.sha, head_repo, head_repo != f"{owner}/{repository}",
        )

    def get_changed_files(self, pr: PullRequestContext) -> list[ChangedFile]:
        pull = self._github.get_repo(f"{pr.owner}/{pr.repository}").get_pull(pr.number)
        return [ChangedFile(file.filename, file.patch or "", file.status) for file in pull.get_files()]

    def publish_review(self, pr: PullRequestContext, summary: str, findings: list[Finding]) -> None:
        pull = self._github.get_repo(f"{pr.owner}/{pr.repository}").get_pull(pr.number)
        comments = [
            {"path": f.path, "line": f.line, "side": f.side, "body": f.body}
            for f in findings if f.path and f.line
        ]
        marker = f"<!-- prscout:{pr.repository}:{pr.number}:{pr.head_sha}:v1 -->"
        pull.create_review(body=f"{marker}\n{summary}", event="COMMENT", comments=comments)
