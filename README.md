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
- `core/`: workspace entry point, database diagnostics, and HTMX-aware login protection.
- `accounts/`: email-based users, registration, session login/logout, and Django admin forms.
- `projects/`: project CRUD, member-scoped access, and admin/member permissions.
- `tasks/`: assigned tasks, priorities, Kanban statuses, ordering, and completion timestamps.
- `templates/base.html`: shared document, styles, scripts, messages, and HTMX CSRF header.
- `templates/components/`: reusable brand, messages, and form-field includes.
- `templates/accounts/`: shared authentication layout and form/logout partials.
- `templates/core/partials/`: small HTML fragments reused by full pages and HTMX responses.
- `static/`: application CSS, HTMX 2.0.11, and SortableJS 1.15.7, served locally with their licenses. No CDN or JavaScript build step is required.
- `templates/workspace/` and `templates/projects/`: reusable application layout, sidebar, project cards, forms, and detail screens.
- `index.html` and `assets/`: simplified standalone Kanban design preview with browser-local demo tasks, not the database-backed app.

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

3. Apply the database schema:

   ```sh
   docker compose exec django python manage.py migrate
   ```

4. Open http://localhost:8001. Sign in or create an account to access your projects. JSON health is at `/health/`.

The custom email user is included in the first accounts migration. The standalone Kanban preview can be served with `python -m http.server 8765 --bind 127.0.0.1`.

The Compose project is named `stride_templates`, using a fresh `stride_templates_postgres_data` volume. The previous `stride_postgres_data` volume is not mounted or modified. PostgreSQL has no host port; Django binds to loopback on port 8001 by default (`DJANGO_PORT` overrides it).

```sh
docker compose exec django python manage.py check
docker compose exec django python manage.py test core.tests accounts.tests projects.tests tasks.tests --verbosity 1
docker compose exec django python manage.py createsuperuser
docker compose logs -f django
docker compose down
```

Do not add `-v` to `down` unless you intend to erase this new database. Source edits hot-reload; Python dependencies live in `/opt/venv` inside the image so the source mount does not hide them. Rebuild after dependency or environment changes.

## Domain models

- Users sign in with email, without usernames. Email is normalized and case-insensitively unique; Django hashes passwords. Django staff/superuser permissions are separate from project roles.
- Each project has a title, description, deadline, and owner. Creation adds the owner as a project admin atomically. The owner cannot be transferred, demoted, or removed through normal model operations.
- A user can have one membership per project, with an admin or member role. Only active users can be added. Removing a membership unassigns that user's tasks in that project, including bulk deletions.
- Tasks belong to a project and record their creator, optional assignee, priority, deadline, status, board position, and timestamps. Assignees must be active members of that project. Completing/reopening a task sets/clears its completion timestamp.
- Database constraints enforce email/membership uniqueness and valid priority, status, and role values. Use validated model saves or ModelForms for domain changes; bulk inserts/updates bypass validation and save hooks. Prefer deactivating accounts: project owners and task creators are protected from deletion.

## Authentication

- `/login/`: email/password sign-in, with safe same-origin return URLs.
- `/register/`: first name, email, password, and confirmation; successful registration signs in a regular, non-staff user.
- `/logout/`: POST only, submitted through the shared sign-out form.
- Authentication uses Django's database-backed sessions and CSRF protection, with password validation and inline errors. Protected HTML is not cached.
- `LoginRequiredMiddleware` protects application views by default. Login, registration, and the public database diagnostics (`/health/`, `/connection/`) are explicitly exempt; static files remain available.

## Projects

- `/` and `/projects/`: only projects you belong to. New accounts start with an empty workspace, not demo projects.
- `/projects/new/`: create a project with a title, description, and deadline. The server sets its owner to the signed-in user.
- `/projects/<id>/`: project task board with creation, details, editing, and deletion dialogs. Tasks appear in To Do, In Progress, Review, and Completed; no demo tasks are inserted into the live workspace.
- `/projects/<id>/members/`: existing project members and their roles.
- `/projects/<id>/settings/`: project details, the existing admin edit action, and owner-only deletion. Members can read settings without gaining edit permission.
- `/projects/<id>/edit/`: update project details; ownership and membership fields cannot be submitted through this form.
- `/projects/<id>/delete/`: owner-only confirmation page. Only a CSRF-protected POST deletes the project and its tasks.
- Outsiders receive 404 responses; insufficient project-role permissions receive 403. Edit/delete writes lock the project row within a transaction.
- Internal navigation and forms use HTMX with full-page fallbacks. Expired sessions trigger a full login navigation; logout stays a normal POST. Private pages opt out of HTMX history snapshots.
- Motion is restrained: short page entries, hover transitions, and an async progress indicator. Reduced-motion preferences disable these animations. Request failures display a dismissible message.
- The live workspace follows the standalone preview's forest-green sidebar, typography, spacing, and board styling. Shared project headers show the deadline and member avatars; Board / Members / Settings are normal accessible navigation links enhanced by HTMX.
- The sidebar lists up to six recent projects belonging to the signed-in user. Mobile navigation uses a native modal drawer with keyboard focus containment and Escape-to-close.

## Tasks

- `/projects/<id>/tasks/new/`: any project member can create a task. The server sets its project and creator; the form accepts only title, description, assignee, priority, deadline, and status.
- `/projects/<id>/tasks/<task-id>/`: all project members can read the full task. Project admins, its creator, and its assignee receive the editable form; other members receive a view-only detail screen.
- `/projects/<id>/tasks/<task-id>/edit/` and `/delete/`: admins can manage all tasks; members can manage tasks they created or are currently assigned to. Permissions are checked again on each write. Deletion requires a confirmation followed by CSRF-protected POST.
- Assignee choices contain only active members of the current project, with an Unassigned option. Invalid titles, dates, priority/status values, and out-of-project or inactive assignees produce inline errors without saving.
- Task dialogs use shared form/detail partials and HTMX. Successful mutations return a fresh board through an out-of-band swap, retaining the page and project header. Ordinary full-page forms also work without JavaScript.
- Dialogs support keyboard focus, Escape/cancel, safe confirmation focus, reduced motion, and draft-preserving failure feedback. After a save, focus moves to the refreshed task; after deletion, it moves to New task.
- Writes lock the project, its memberships, and the edited task inside a transaction. New tasks and status changes append to their destination column; completion timestamps follow the model's existing rules.
- Task handles support mouse dragging and touch long-press dragging between columns and within a column. Focus a handle and use Up/Down to reorder or Left/Right to change columns. Handles appear only for tasks the current user can manage; the server checks permissions again on every move.
- `/projects/<id>/tasks/<task-id>/move/`: CSRF-protected POST accepting a valid `status` and optional `before_id` destination task. The server derives positions, rejects stale/out-of-project insertion points, and saves status, order, and completion timestamps atomically. Moves do not modify titles, assignments, or other task fields.
- The board shows its last confirmed layout while a move saves, then renders the server's fresh board without navigating away. Focus returns to the moved handle and its column/position is announced. Failed moves show a refresh notice and disable further drag/keyboard moves until the board is refreshed; uncertain writes are not retried automatically.
- Drag controls reinitialize after navigation and task dialog saves. Reduced motion disables sorting animation. Without JavaScript, task links and full-page forms remain available to change status.

Adding/removing members and dashboard charts remain deferred. The member list is still read-only.

This is a development configuration. Secure cookie flags default to false for local HTTP and must be enabled for an HTTPS deployment.
