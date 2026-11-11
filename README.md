# Stride

Django templates + HTMX + PostgreSQL. No React, DRF, frontend container, or JavaScript build pipeline.

## Project foundation

Generated with Django's commands:

```sh
uv run django-admin startproject config .
uv run django-admin startapp core
uv run django-admin startapp accounts
uv run django-admin startapp projects
uv run django-admin startapp tasks
```

- `config/`: settings and root URLs.
- `core/`: foundation page, database health endpoint, and HTMX status partial.
- `accounts/`, `projects/`, `tasks/`: domain apps; models follow the scaffold checkpoint.
- `templates/base.html`: shared document, styles, scripts, messages, and HTMX CSRF header.
- `templates/components/`: reusable brand, messages, and form-field includes.
- `templates/core/partials/`: small HTML fragments reused by full pages and HTMX responses.
- `static/`: application CSS and locally served HTMX 2.0.11, including its license.
- `index.html` and `assets/`: original approved Kanban design, unchanged.

Use template inheritance for page layouts and `{% include %}` for shared UI. Future sidebar, task-card, column, and form fragments should render the same partial on initial requests and asynchronous updates; do not duplicate separate full-page/HTMX markup.

## Run locally

Requirements: Docker with Compose. Python dependencies are locked in `uv.lock`.

1. Copy `.env.example` to `.env` and replace both secret placeholders with separate random values:

   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. Build and start the two services:

   ```sh
   docker compose up --build -d --wait
   ```

3. Open http://localhost:8001. The foundation page's connection button updates a reusable partial through HTMX. JSON health is at `/health/`.

At the scaffold checkpoint, migrations are deliberately not applied: the custom email user must be introduced first. The original standalone design can still be previewed with `python -m http.server 8765 --bind 127.0.0.1`.

The Compose project is named `stride_templates`, using a fresh `stride_templates_postgres_data` volume. The previous `stride_postgres_data` volume is not mounted or modified. PostgreSQL has no host port; Django binds to loopback on port 8001 by default (`DJANGO_PORT` overrides it).

```sh
docker compose exec django python manage.py check
docker compose exec django python manage.py test core.tests --verbosity 1
docker compose logs -f django
docker compose down
```

Do not add `-v` to `down` unless you intend to erase this new database. Source edits hot-reload; Python dependencies live in `/opt/venv` inside the image so the source mount does not hide them. Rebuild after dependency or environment changes.

This is a development configuration. Secure cookie flags default to false for local HTTP and must be enabled for an HTTPS deployment. No domain CRUD, authentication pages, real board, or chart has been implemented yet; the original design remains a reference rather than a completed Django screen.
