# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Collaboration Style
- This project is a learning exercise. Act as a tutor, not a code generator.
- Do NOT write code or edit files unless explicitly asked to.
- Explain concepts, point out issues, discuss best practices, and suggest approaches - let the user implement.
- Reading and searching the codebase (Read, Grep, find, etc.) is encouraged — use tools freely to ground your explanations in the actual code rather than guessing. The restriction above applies only to writing/editing code.

## Project Overview

Resume Store is a FastAPI backend that tailors resumes to job descriptions using the Anthropic API. Users submit their job history and a target job description; the app constructs a prompt from Jinja2 templates and a per-user customizable system prompt, then calls Claude to produce a tailored resume (summary + rewritten job bullets). Auth is JWT-based (argon2 password hashing via pwdlib).

## Commands

### Run the app
```bash
docker compose up -d          # Postgres on localhost:5555
uv run alembic upgrade head   # Apply migrations
uv run playwright install chromium  # One-time browser install for PDF rendering
uv run uvicorn app.main:app --reload
```

### Lint / format
```bash
uv run ruff check --fix .     # Lint (excludes alembic/)
uv run ruff format .          # Format
```

Pre-commit hooks run ruff check + format automatically on commit.

### Tests
```bash
uv run python -m unittest discover -s tests -v
RUN_PDF_INTEGRATION_TESTS=1 uv run python -m unittest discover -s tests -v
```

Tests use the standard-library `unittest` framework. Chromium-backed PDF integration
tests are opt-in via `RUN_PDF_INTEGRATION_TESTS=1`; the rest run without a browser.

### Migrations
```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

Alembic env.py reads `DATABASE_URL` from `.env` via `get_settings()`, not from `alembic.ini`.

## Architecture

### App structure
- `app/main.py` — FastAPI app setup, CORS middleware (environment-aware), router registration
- `app/routes/` — routers split by domain: `auth.py`, `profile.py`, `prompt.py`, `resume.py`
- `app/services/` — business logic: `auth.py`, `user_data.py`, `resume.py`, `prompts.py`
- `app/core/render.py` — managed Playwright/Chromium PDF renderer and local resume-asset routing
- `app/templates/resume_templates/` — shared resume macros/CSS and the classic, sidebar,
  and multipanel layouts
- `app/core/dependencies.py` — shared FastAPI dependencies (`SessionDep`, `CurrentUserDep`, `get_current_user`)

### Key flow: `POST /resume/new`
1. `CurrentUserDep` authenticates the user via JWT; route receives `ResumeRequest` (filename + `LLMInput`)
2. `services/resume.py` validates filename uniqueness, loads the user's `UserProfile` (requires personal info), then calls `send_message()` which renders Jinja2 templates, loads the custom prompt (or falls back to `DEFAULT_USER_PROMPT`), and calls `client.messages.parse()` with structured output (`LLMOutput`)
3. System prompt = `base_prompt.j2` (role/instructions) + user's prompt row (tailoring rules)
4. LLM output is combined with profile data (personal info, education, projects, skills) into a `ResumeData` composite, persisted as a `Resume` row, and `ResumeMetadata` (id, filename, timestamps) is returned

### Auth system
- Registration (`POST /auth/signup`) requires an `invite_code` and returns a `Token` directly (user is logged in on signup)
- A `UserPrompt` row with the default prompt is created automatically on registration
- Constant-time dummy hash comparison on failed lookups to prevent user enumeration

### Prompt system
- `templates/base_prompt.j2` — core system instructions (what the AI does)
- `templates/default_user_prompt.j2` — default tailoring rules, loaded at import time via `services/prompts.py`
- `templates/user_message.j2` — structures user input (instructions, JD, job history) as XML
- Each user has a `UserPrompt` row; can be updated via `/prompt/update`, reset by sending empty string

### Resume system
- Full CRUD via `app/routes/resume.py`: `POST /resume/new`, `GET /resume/`, `GET /resume/{id}`, `PUT /resume/{id}`, `DELETE /resume/{id}`
- `Resume` model stores `llm_input`, `llm_output`, and `resume_data` as JSON columns, plus `filename` (unique per user via DB constraint)
- `ResumeData` is the composite schema: personal info + summary + jobs + education + projects + skills
- `LinkableText` (`text` plus optional `url`) is used for personal-info `extras` and
  project `title`. Its pre-validator accepts legacy strings and converts them to
  unlinked values, so existing stored JSON and clients remain compatible.
- Link URLs accept only `http`/`https`. Scheme-less dotted hostnames receive an
  `https://` prefix; blank URLs become `None`. Scheme-relative URLs, credentials,
  whitespace, invalid ports, non-web schemes, and scheme-less bare hosts are rejected.
- Resume Jinja environments enable HTML autoescaping. The shared `linkable` macro
  renders linked and plain values consistently in every layout, and `.resume-link`
  provides visible underlining. Chromium retains these anchors as PDF link annotations.
- `ResumeMetadata` (id, filename, created_at, updated_at) is returned from generate and list endpoints
- Custom `DuplicateFilenameError` raised on filename conflicts

### PDF rendering
- `PDFManager` owns a shared Playwright instance and Chromium browser, with a semaphore
  limiting concurrent renders and separate capacity/render timeouts.
- Resume assets are served only from `app/templates/resume_templates/` through an
  intercepted `http://resume-assets.local/` URL; traversal and unsupported asset types
  are rejected.
- `pypdf` validates generated PDFs and reports their page count.

### Profile system
- `UserProfile` model stores personal info, job/education/project history, and skills as JSON columns
- Profile list fields (jobs, education, projects, skills) return empty lists when no data exists
- Personal info returns 404 when not yet set

### Data layer
- Async SQLAlchemy with asyncpg; Postgres 16 via Docker Compose (port 5555)
- Models in `models/base.py`: `User`, `UserPrompt` (1:1 with User), `UserProfile` (1:1 with User, JSON columns for profile data), `Resume` (many per User, unique filename per user)
- Pydantic schemas in `schemas/base.py` use camelCase aliases (`alias_generator=to_camel`) for frontend compatibility

### Config
All settings loaded from `.env` via pydantic-settings (`core/config.py`): `DATABASE_URL`, `ENVIRONMENT`, `INVITE_CODE`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_TOKEN_EXPIRES`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS`.

## Style

- Python 3.13+, managed with uv
- Ruff: line-length 88, rules E/F/I/UP, double quotes
- Tests use `unittest`; keep fast schema/template tests separate from opt-in Chromium
  integration coverage.
