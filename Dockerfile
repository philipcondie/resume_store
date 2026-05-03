FROM python:3.13.11-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \                                                                                
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN uv sync --no-dev

COPY . /app/

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uv","run","uvicorn","app.main:app","--host","0.0.0.0", "--port", "8000"]