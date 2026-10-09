# Docker setup

Last updated: 2026-10-09

How the local Docker setup is built and why. To start it, see Option A in
the main [README.md](../../README.md#option-a-docker-recommended). It is for local
development only. Production doesn't use Docker (see
[operations/server_setup.md](../operations/server_setup.md)).

## Files

| File                              | What it does                                               |
| --------------------------------- | ---------------------------------------------------------- |
| `Dockerfile.dev`                  | Builds the Django container: Python 3.12 and the packages from `requirements.txt` |
| `docker-compose.yml`              | Runs two containers: `db` (PostgreSQL 16) and `web` (Django) |
| `.devcontainer/devcontainer.json` | Lets VS Code open the `web` container ("Reopen in Container"). Shows the whole repo; new terminals start in `ifiplatform/` |
| `.dockerignore`                   | Keeps the venv, local database, media and `.env` out of the build |

## What happens on start

1. `db` starts. `web` waits until the database answers (the healthcheck).
2. `web` runs `migrate`, then `seed_dev_data`, then `runserver`.
   `seed_dev_data` skips what already exists, so it's safe to run on
   every start.
3. The site is served at `localhost:8000`.

The repo is shared into the container at `/workspace`, so file edits on
your own computer show up right away and `runserver` reloads.

## Why it's built this way

- **Commands stay the same.** Students work inside the container
  (VS Code's terminal, or `docker compose exec web bash`), so the
  README's `python manage.py ...` commands work unchanged. `py` is
  linked to `python` in the container, so the Windows style works too.
- **No `.env` needed.** `web` sets every needed setting in
  `docker-compose.yml`. A student's own `ifiplatform/.env` can't override
  them, because python-dotenv never replaces a variable that is already
  set. The same `.env` keeps working with SQLite outside Docker.
- **Same versions as production:** Python 3.12 and PostgreSQL 16.
- **Ports only on your own computer.** Both ports are bound to
  `127.0.0.1`, so nobody else on the network (like event Wi-Fi) can reach
  the site with its `admin`/`admin` user, or the database.
- **Database on port 5433, not 5432,** so it doesn't clash with a
  PostgreSQL the student already has installed.
- **Start commands are written inline in `docker-compose.yml`,** not in a
  `.sh` script. On Windows, Git can turn a script's line endings into
  CRLF, which breaks it in Linux.
- **Code isn't copied into the image.** It's shared in instead, so the image
  only needs rebuilding when `requirements.txt` changes.

## Security

The password (`devpassword`) and secret key in `docker-compose.yml` are
fake and only for local use. Never reuse them on a server.
