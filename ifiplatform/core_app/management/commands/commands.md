# core_app management commands

## compile_translations

```bash
py manage.py compile_translations
```

Compiles `.po` translation files to `.mo` using `polib`, without needing
the system `gettext` tools (`msgfmt`) Django's own `compilemessages`
requires. Not all dev machines have `gettext` installed, and installing it
needs admin rights (common friction on Windows) — `polib` is already a
dependency via `wagtail_localize`, so this is a pure-Python drop-in
substitute for local dev. If you do have `msgfmt` available, plain
`manage.py compilemessages` works exactly the same and there's no need for
this command. Only compiles this project's own `.po` files (under each
app's `locale/`, plus `ifiplatform/locale/`), never a third-party
package's.

## announce_deploy

```bash
py manage.py announce_deploy [--minutes N] [--clear]
```

Operational, not a dev command — sets the shared "a deploy is imminent"
flag that powers the site-wide countdown banner, read by the deploy
workflow (`.github/workflows/ci-deploy.yml`) before restarting the server.
You shouldn't need to run this yourself in local dev.

## clear_cache

```bash
py manage.py clear_cache
```

Clears the site-wide cache (see `settings.py`'s `CACHES` — a `FileBasedCache`
persisted on disk under `django_cache/`, so it survives server restarts and,
notably, isn't touched by `git reset --hard` during a deploy since that
directory is untracked). Wired into `ci-deploy.yml`, running right after
every deploy's gunicorn restart.

Exists because of a real incident: after some deploys, Wagtail's own
site-root-paths cache went stale relative to the actual page tree, and
every `Page.url` silently resolved to `None` — turning every `{% pageurl %}`
link across the site into a literal `/en/None/`-style URL for every
visitor, since this cache is shared site-wide, not per-user. Safe to run
any time; clearing a cache never loses real data, it just means the next
request recomputes whatever it needed. Also useful in local dev if you see
the same "links resolve to None" symptom after moving pages around or
reseeding the database.
