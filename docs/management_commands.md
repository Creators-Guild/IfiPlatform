# Custom manage.py commands

This project's own `manage.py` commands, beyond Django's built-in ones
(`migrate`, `createsuperuser`, `test`, `makemessages`/`compilemessages`,
etc. — see the main [README.md](../README.md) for those).

## seed_dev_data

```bash
py manage.py seed_dev_data
```

Fills a fresh local database with a dummy article tree (index pages,
categories, a test article, a test student union, a test tool, and a
sample event) so you're not starting from a blank site. Covered in the
main setup flow — see [README.md](../README.md#6-fill-database-with-dummy-datarecommended).

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

## sync_deepl_glossary

```bash
py manage.py sync_deepl_glossary
```

Pushes `ifi_home_app/translation/glossary_terms.py`'s nb → en term list to
DeepL as a glossary, so DeepL honours those exact translations (or "don't
translate this," for proper nouns like tool/union names) on every
machine-translation call this project makes. DeepL glossaries can't be
edited in place, so this deletes any existing glossary with the same name
and recreates it — safe to re-run whenever `glossary_terms.py` changes.

Requires `DEEPL_API_KEY` set in `.env`. **One-time manual step after
running it:** copy the printed `glossary_id` into `DEEPL_GLOSSARY_ID` in
`.env` and restart the server.

## sync_translated_page_fields

```bash
py manage.py sync_translated_page_fields [--dry-run]
```

Re-syncs wagtail-localize `SynchronizedField`s (`show_in_menu`, `status`,
etc.) from every nb page to its existing English translation. This is a
one-off catch-up command for pages that drifted out of sync *before* the
automatic sync hook (`ifi_home_app/wagtail_hooks.py`) existed — you're
unlikely to need it unless you're working with a database seeded before
that hook was added. Safe to re-run: re-syncing an already-synced page is
a no-op. `--dry-run` lists what would be synced without changing anything.

## cleanup_unverified_accounts

```bash
py manage.py cleanup_unverified_accounts [--dry-run]
```

Deletes signups that never confirmed their email address
(`is_active=False` until `verify_email_view` flips it — see
`account_app.views.login_views`) once they're older than
`settings.UNVERIFIED_ACCOUNT_RETENTION_DAYS` (7 days by default). Exists
for GDPR storage-limitation (Art. 5(1)(e)) — no reason to keep a
name/email on file for an account nobody ever actually claimed. A plain
delete is safe here (unlike `account_app.views.account_views.
delete_account_view`) since an unverified account can never have authored
content or hold permissions.

No task scheduler exists in this project (no Celery/django-crontab) — this
is meant to be invoked periodically from *outside* Django entirely (host
cron, or your platform's own scheduled-job feature). Nothing runs it for
you automatically. Safe to re-run. `--dry-run` lists matching accounts
without deleting them.

## announce_deploy

```bash
py manage.py announce_deploy [--minutes N] [--clear]
```

Operational, not a dev command — sets the shared "a deploy is imminent"
flag that powers the site-wide countdown banner, read by the deploy
workflow (`.github/workflows/ci-deploy.yml`) before restarting the server.
You shouldn't need to run this yourself in local dev.
