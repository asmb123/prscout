from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import ConfigurationError, github_token, load_review_config
from app.gith.client import PyGithubClient
from app.graph import build_review_graph
from app.llm import GroqReviewProvider


def main() -> int:
    load_dotenv(Path(__file__).with_name(".env"))
    load_dotenv()
    parser = argparse.ArgumentParser(description="Review a GitHub pull request.")
    parser.add_argument("--event", default=os.getenv("GITHUB_EVENT_PATH"))
    args = parser.parse_args()
    if not args.event:
        raise ConfigurationError("GITHUB_EVENT_PATH or --event is required")
    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    pull = event.get("pull_request")
    repository = event.get("repository", {}).get("full_name", "")
    if not pull or "/" not in repository:
        raise ConfigurationError("Expected a pull_request event payload")
    owner, name = repository.split("/", 1)
    client = PyGithubClient(github_token())
    pr = client.get_pull_request(owner, name, int(pull["number"]))
    config = load_review_config(Path.cwd())
    primary = GroqReviewProvider()
    fallback_model = os.getenv("GROQ_FALLBACK_MODEL")
    fallback = (
        GroqReviewProvider(model=fallback_model)
        if fallback_model and fallback_model != primary.model
        else None
    )
    graph = build_review_graph(
        config,
        primary,
        fallback,
        github=client,
        working_directory=str(Path.cwd()),
    )
    result = graph.invoke({"pr": pr, "files": client.get_changed_files(pr)})
    if result.get("error"):
        print(result["error"], file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
