# Image Processing Service

A backend service for uploading, transforming, and retrieving images — similar in spirit to Cloudinary. Built as a practice project following the [roadmap.sh Image Processing Service](https://roadmap.sh/projects/image-processing-service) spec.

## Description

Users can register, log in, upload images, and apply transformations (resize, crop, rotate, flip, mirror, grayscale, sepia, format conversion, compression). Transformations run asynchronously via a Celery worker so the API responds immediately with a job id, and results are cached in Redis so identical transform requests aren't reprocessed. Every derived image keeps a link back to its source, and deleting a source image cascades to everything derived from it.

## Tech stack

- **FastAPI** — HTTP API, request validation, docs
- **PostgreSQL** + **SQLAlchemy** + **Alembic** — data storage and migrations
- **Redis** — response caching and rate-limit counters
- **Celery** — asynchronous image transformation
- **AWS S3** (boto3) — image storage
- **Pillow** — image transformations
- **JWT** (PyJWT) + **bcrypt** — authentication
- **slowapi** — rate limiting
- **Docker Compose** — local orchestration (app, worker, Postgres, Redis)
- **pytest** + **mypy** (strict) — testing and type checking
- **uv** — Python package management

## Project structure

```
.
├── docker-compose.yml
├── .github/workflows/    # CI (tests + mypy)
├── app/main.py           # FastAPI app instance, router registration
├── api/
│   ├── deps.py           # auth dependency (get_current_user)
│   └── routes/           # auth (signup/login/me), images (upload/transform/status/get/list/delete)
├── core/                 # config (Settings), security (JWT/hashing), storage (S3),
│                         # transforms (Pillow), cache (Redis), celery app + task, rate limiting
├── db/                   # SQLAlchemy engine/session, declarative Base
├── models/               # User, Image
├── schemas/              # Pydantic request/response schemas
├── alembic/              # migrations
├── scripts/
│   └── init-test-db.sql  # auto-creates the test DB on first Postgres init
├── tests/                # pytest suite (auth, images, transforms)
├── Dockerfile
└── pyproject.toml
```

## Installation

**Prerequisites:** Docker Desktop, an AWS account with an S3 bucket + IAM credentials (or adapt `core/storage.py` for another S3-compatible provider like Cloudflare R2).

1. Clone the repo and copy the environment template:
   ```
   cp .env.example .env
   ```
2. Fill in `.env`: a real `JWT_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`), and your `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` / `AWS_S3_BUCKET`.
3. Build and start everything:
   ```
   docker compose up --build -d
   ```
4. Run database migrations:
   ```
   docker compose exec app alembic upgrade head
   ```
5. Open `http://localhost:8000/docs` — sign up, log in, authorize, and try the endpoints.

## Testing

Tests run against a real local Postgres/Redis (exposed by `docker-compose.yml` on `localhost`), with S3 and Celery mocked/eager — no AWS calls or a running worker required.

```
uv sync
uv run pytest
```

`TEST_DATABASE_URL` / `TEST_REDIS_URL` in `.env` point tests at an isolated test database and a separate Redis db index, so test runs never touch your dev data.

## Coverage

```
uv run pytest --cov=. --cov-report=term-missing
```

For a browsable, file-by-file report:

```
uv run pytest --cov=. --cov-report=html:.coverage_data/htmlcov
start .coverage_data/htmlcov/index.html
```

For inline gutters in VS Code, install the **Coverage Gutters** extension and generate the Cobertura XML format instead:

```
uv run pytest --cov=. --cov-report=xml:.coverage_data/coverage.xml
```

(Both report types can be generated in the same run by passing `--cov-report` twice.)

## Type checking

```
uv run mypy .
```

Configured `strict = true` in `pyproject.toml`, with a relaxed override for `tests/` (fixture parameters aren't annotated) and third-party libraries lacking type stubs (`boto3`, `botocore`).

## CI

Two GitHub Actions workflows run on every push and pull request to `main`:

- **`.github/workflows/test.yml`** — spins up ephemeral Postgres and Redis service containers, installs dependencies with `uv`, and runs the full test suite with coverage.
- **`.github/workflows/mypy.yml`** — runs `mypy .` in strict mode.