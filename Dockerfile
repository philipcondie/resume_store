FROM python:3.13.11-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

RUN useradd --create-home --shell /bin/bash app

COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen --no-install-project \
    && chown -R app:app /app

# shared user independent location for playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN uv run playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* \
    && chown -R app:app /ms-playwright

USER app
COPY --chown=app:app . /app/

EXPOSE 8000

CMD ["uv","run","uvicorn","app.main:app","--host","0.0.0.0", "--port", "8000"]
