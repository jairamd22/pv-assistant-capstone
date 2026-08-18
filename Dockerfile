FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml ./
# If you've committed uv.lock (recommended: run `uv lock` once), use:
#   COPY pyproject.toml uv.lock ./
#   RUN uv sync --locked
RUN uv sync

COPY . .

EXPOSE 8000
CMD ["uv", "run", "chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
