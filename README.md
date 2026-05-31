# Resume Store

A FastAPI backend that tailors resumes to job descriptions using the Anthropic API.

Users submit their job history and a target job description; the app builds a prompt
from Jinja2 templates and a per-user customizable system prompt, then calls Claude to
produce a tailored resume (a summary plus rewritten job bullets). Generated resumes can
be styled with multiple layouts and exported to PDF.

## Features

- **AI resume tailoring** — combines your profile, a job description, and custom
  instructions into a tailored resume via Claude (structured output).
- **JWT authentication** — signup/login with argon2 password hashing (pwdlib);
  registration is gated behind an invite code.
- **Profile management** — store personal info, job/education/project history, and
  skills as structured data.
- **Customizable prompts** — each user has an editable tailoring prompt, with a sensible
  default.
- **Layouts & styling** — render resumes with multiple layout templates and per-resume
  styling.
- **PDF export** — download generated resumes as PDF (WeasyPrint).

## Tech stack

- **Python 3.13+**, managed with [uv](https://docs.astral.sh/uv/)
- **FastAPI** + **Uvicorn**
- **SQLAlchemy 2.0** (async) with **asyncpg**, **PostgreSQL 16**
- **Alembic** for migrations
- **Pydantic** / **pydantic-settings** for schemas and config
- **Anthropic** SDK for LLM calls
- **Jinja2** for prompt and layout templating
- **WeasyPrint** for PDF generation
- **Ruff** for linting/formatting, **pre-commit** hooks

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for the Postgres container)
- An Anthropic API key

### Setup

```bash
# Install dependencies
uv sync

# Copy the example env file and fill in your values
cp .env.example .env

# Start Postgres (exposed on localhost:5555)
docker compose up -d

# Apply database migrations
uv run alembic upgrade head

# Run the app
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at
`http://127.0.0.1:8000/docs`.

### Configuration

All settings are loaded from `.env` via pydantic-settings. See `.env.example` for the
full list, which includes:

- `DATABASE_URL`
- `ENVIRONMENT`
- `INVITE_CODE` — required to register a new user
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_TOKEN_EXPIRES`
- `ANTHROPIC_API_KEY`
- `CORS_ORIGINS`

## API overview

| Area    | Endpoint                          | Description                          |
| ------- | --------------------------------- | ------------------------------------ |
| Auth    | `POST /auth/signup`               | Register (requires invite code)      |
|         | `POST /auth/login`                | Log in, returns a JWT                 |
| Profile | `GET/POST /profile/personal_info` | Personal info                        |
|         | `GET/POST /profile/jobs`          | Job history                          |
|         | `GET/POST /profile/education`     | Education history                    |
|         | `GET/POST /profile/projects`      | Projects                             |
|         | `GET/POST /profile/skills`        | Skills                               |
| Prompt  | `GET /prompt`                     | Get your tailoring prompt            |
|         | `POST /prompt/update`             | Update (or reset) your prompt        |
| Resume  | `POST /resume/new`                | Generate a tailored resume           |
|         | `GET /resume`                     | List resumes                         |
|         | `GET /resume/{id}`                | Get a resume                         |
|         | `PUT /resume/{id}`                | Update a resume                      |
|         | `PUT /resume/{id}/layout`         | Change a resume's layout             |
|         | `POST /resume/{id}/duplicate`     | Duplicate a resume                   |
|         | `GET /resume/{id}/pdf`            | Export a resume as PDF               |
|         | `DELETE /resume/{id}`             | Delete a resume                      |
| Layout  | `GET /layout`                     | Get layout options                   |
|         | `POST /layout/update`             | Update layout                        |
|         | `GET /layout/styling`             | Get styling                          |
|         | `POST /layout/styling/update`     | Update styling                       |
| Health  | `GET /health`                     | Health check                         |

## Development

```bash
# Lint and auto-fix
uv run ruff check --fix .

# Format
uv run ruff format .

# Create a new migration after model changes
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

Pre-commit hooks run ruff check + format automatically on commit.

## License

[MIT](LICENSE) © Philip Condie
