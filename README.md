# Stride

A project management app built with Django, HTMX, PostgreSQL, and Redis.

## Features

- Email login and registration.
- Projects with admin/member roles.
- Kanban boards with draggable tasks, priorities, deadlines, search, and filters.
- My Tasks across your projects.
- Live dashboard with task totals, a status chart, and upcoming deadlines.
- Persistent notification bell for assignments and project additions.

Live updates use WebSockets, without timed polling.

## Setup

Requires Docker with Docker Compose. Run commands from the project folder.

1. Copy the example configuration:

```sh
cp .env.example .env
```

2. Open `.env` and replace the `SECRET_KEY` and `POSTGRES_PASSWORD` placeholders with separate random values. Keep `.env` private.

3. Start the app and create the database tables:

```sh
docker compose up --build -d --wait
docker compose exec django python manage.py migrate
```

4. Open http://localhost:8001 and create an account or sign in.

## Useful commands

View logs:

```sh
docker compose logs -f django
```

Restart after Python changes:

```sh
docker compose restart django
```

Stop the app:

```sh
docker compose down
```

Your data stays in the database volume. Adding `-v` to the stop command deletes it.

## Demo accounts

The prepared demo database includes these accounts. Password for all: `stride123`.

- `alex@stride.test` — admin across all demo projects.
- `jamie@stride.test`
- `morgan@stride.test`
- `sam@stride.test`
- `taylor@stride.test`

These accounts are for local demos and are not created automatically on a fresh database.

## Load demo data

To populate a fresh database with demo accounts, projects, tasks, and notifications:

```sh
docker compose exec django python manage.py seed_demo --reset
```

This creates 5 accounts, 3 projects, 36 tasks, and 36 notifications. Password for all demo accounts: `stride123`.

## Notes

- Dashboard totals cover projects you belong to; My Tasks shows only your assignments.
- The bell supports read/unread notifications and Mark all as read.
- This is a local development setup, not a production deployment configuration.