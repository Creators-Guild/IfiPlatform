# ifi_home_app management commands

## seed_dev_data

```bash
py manage.py seed_dev_data [--force]
```

Fills a fresh local database with a dummy article tree (index pages,
categories, a test article, a test student union, a test tool, and a
sample event) so you're not starting from a blank site. Covered in the
main setup flow — see [README.md](../../../../../README.md#6-fill-database-with-dummy-datarecommended).

Refuses to run when `DEBUG` is off, as a guard against accidentally
seeding dummy data into what looks like a real (non-local) database.
`--force` overrides that check — mainly useful in tests, since Django's
test runner always forces `DEBUG=False` regardless of `.env`.

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

## sync_peoply_events

```bash
py manage.py sync_peoply_events [--after YYYY-MM-DD]
```

Creates `EventPage`s from [Peoply](https://peoply.app) (the event platform
IFI's student unions actually use), one per `UnionPage` that has a
`peoply_organization_id` set (found in the union's own Peoply page URL —
edit the union in wagtail-admin to set it, enabling sync for that union).

`--after` limits the sync to events starting on/after that date; defaults
to today, so a plain run only ever picks up upcoming events.

**Create-only**: an event already synced (matched by
`external_source="peoply"` + `external_uid`, Peoply's own event ID) is
skipped on every later run, even if it changed on Peoply's side or an
editor has since hand-edited it here — sync only ever *adds*, it never
overwrites or removes anything. Re-running this is a way to catch new
events, not to keep an already-synced one's details live-updated; if a
venue or time changes on Peoply after the fact, that has to be corrected
on the `EventPage` by hand.

New events are created nb-only (untranslated) and published immediately.
`event_type` is inferred from the title — defaults to `"social"`, upgrades
to `"company"` when the title contains "Bedriftspresentasjon"; anything
else (deadline, academic) needs manual correction, since Peoply doesn't
expose a comparable category itself.

### Automatic scheduling

A systemd timer runs this automatically on the production server — every 6
hours (00:00/06:00/12:00/18:00), plus one extra run at 14:00 on weekdays.
Unlike `cleanup_unverified_accounts` (see
[account_app's own commands doc](../../../account_app/management/commands/commands.md)),
this one doesn't need to be invoked from an external scheduler by hand —
the unit files live in [deploy/systemd/](../../../../../deploy/systemd/)
and are checked into the repo.

The service also runs `sync_locale_trees` (wagtail-localize's own command)
right after, to create each newly-synced event's English alias page.
`sync_peoply_events` creates pages via `add_child()`/`save_revision().
publish()` directly, which bypasses wagtail-admin's `after_create_page`
hook — the one thing that would otherwise create that alias automatically.
Without it, a synced event has no English URL at all, and switching
language on its page silently lands on the events overview instead (the
nearest translated ancestor — see `site_tags.translated_page_url`). Safe
to run every time: `sync_locale_trees` only ever creates an alias for a
page that has neither a real translation nor an alias yet, so it's a
no-op for anything already caught up.

No manual server-side setup needed — `.github/workflows/ci-deploy.yml`'s
deploy job copies `deploy/systemd/*` into `/etc/systemd/system/` and runs
`daemon-reload` + `enable --now` on every deploy. All three are idempotent
(a no-op once nothing's changed), so this runs unconditionally on every
deploy rather than needing its own separate first-time step, and any
future change to these unit files takes effect on the next deploy
automatically. To do the same thing by hand (e.g. testing a unit-file
change before it's merged):
```bash
sudo cp deploy/systemd/sync-peoply-events.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sync-peoply-events.timer
```

The 14:00 weekday run is meant as Norway-local time — `OnCalendar=` uses
the server's own system timezone, so check `timedatectl` on the server; if
it reports `UTC`, either `sudo timedatectl set-timezone Europe/Oslo` or add
an explicit ` Europe/Oslo` suffix to both `OnCalendar=` lines in
`sync-peoply-events.timer`.

To check on it:
```bash
systemctl status sync-peoply-events.timer   # is it enabled, when's the next run
systemctl list-timers sync-peoply-events.timer
journalctl -u sync-peoply-events.service    # output from past runs
```
To trigger a run immediately, independent of the schedule:
```bash
sudo systemctl start sync-peoply-events.service
```
