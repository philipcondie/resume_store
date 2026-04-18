# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Collaboration Style
- This project is a learning exercise. Act as a tutor, not a code generator.
- Do NOT write code or edit files unless explicitly asked to.
- Explain concepts, point out issues, discuss best practices, and suggest approaches - let the user implement. 

## Project Overview

Resume Store is a FastAPI backend that tailors resumes to job descriptions using the Anthropic API. Users submit their job history and a target job description; the app constructs a prompt from Jinja2 templates and a per-user customizable system prompt, then calls Claude to produce a tailored resume (summary + rewritten job bullets). Auth is JWT-based (argon2 password hashing via pwdlib).

## Commands

### Run the app
```bash
docker compose up -d          # Postgres on localhost:5555
uv run alembic upgrade head   # Apply migrations
uv run uvicorn app.main:app --reload
```

### Lint / format
```bash
uv run ruff check --fix .     # Lint (excludes alembic/)
uv run ruff format .          # Format
```

Pre-commit hooks run ruff check + format automatically on commit.

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
- `app/core/dependencies.py` — shared FastAPI dependencies (`SessionDep`, `CurrentUserDep`, `get_current_user`)

### Key flow: `POST /resume/new`
1. `CurrentUserDep` authenticates the user via JWT; route receives `ResumeRequest` (filename + `LLMInput`)
2. `services/resume.py` validates filename uniqueness, loads the user's `UserProfile` (requires personal info), then calls `send_message()` which renders Jinja2 templates, loads the custom prompt (or falls back to `DEFAULT_USER_PROMPT`), and calls `client.messages.parse()` with structured output (`LLMOutput`)
3. System prompt = `base_prompt.j2` (role/instructions) + user's prompt row (tailoring rules)
4. LLM output is combined with profile data (personal info, education, projects, skills) into a `ResumeData` composite, persisted as a `Resume` row, and `ResumeMetadata` (id, filename, timestamps) is returned

### Auth system
- Registration (`POST /auth/new`) requires an `invite_code` and returns a `Token` directly (user is logged in on signup)
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
- `ResumeMetadata` (id, filename, created_at, updated_at) is returned from generate and list endpoints
- Custom `DuplicateFilenameError` raised on filename conflicts

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
- No test framework configured yet (tests/ directory is empty)