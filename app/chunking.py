import tiktoken
from dataclasses import replace

from app.models import ChangedFile

MAX_DIFF_TOKENS = 2500

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def chunk_files(
    files: list[ChangedFile],
    max_tokens: int = MAX_DIFF_TOKENS,
) -> list[list[ChangedFile]]:

    chunks = []
    current = []
    current_tokens = 0

    for file in files:
        patch = file.patch or ""
        file_tokens = count_tokens(patch)

        if file_tokens > max_tokens:
            lines = patch.splitlines(keepends=True)
            segment = []
            segment_tokens = 0

            for line in lines:
                tokens = count_tokens(line)

                if segment and segment_tokens + tokens > max_tokens:
                    chunks.append([replace(file, patch="".join(segment))])
                    segment = []
                    segment_tokens = 0

                segment.append(line)
                segment_tokens += tokens

            if segment:
                chunks.append([replace(file, patch="".join(segment))])

            continue

        if current and current_tokens + file_tokens > max_tokens:
            chunks.append(current)
            current = []
            current_tokens = 0

        current.append(file)
        current_tokens += file_tokens

    if current:
        chunks.append(current)

    return chunks
