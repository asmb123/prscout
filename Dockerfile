FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock Readme.md ./
COPY app ./app
COPY .agent-review.md.example ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 reviewer \
    && chown -R reviewer:reviewer /app

USER reviewer

ENTRYPOINT ["uv", "run", "--frozen", "python", "-m", "app.cli"]