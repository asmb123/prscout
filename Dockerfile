FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN pip install --no-cache-dir uv && uv pip install --system .
COPY .agent-review.md.example ./
RUN useradd --create-home --uid 10001 reviewer
USER reviewer
ENTRYPOINT ["python", "-m", "app.cli"]
