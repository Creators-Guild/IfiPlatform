# Homepage opening hours box — design rationale

Last updated: 2026-11-13
Covers: ifiplatform/apps/ifi_home_app/models/opening_hours.py, ifiplatform/apps/ifi_home_app/templates/home/partials/openinghours/openinghours.html, ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_openinghours.css, ifiplatform/apps/ifi_home_app/management/seed_dev_data/opening_hours.py

The side-column box saying, per IFI place, whether it's open right now.
The user chose every behaviour below on 2026-11-13 (design: variant B of
a mockup page); don't change them without asking.

## Data

- `Location` (snippet "Opening hours", `LocationViewSet` in
  `wagtail_hooks.py`) with inline `OpeningPeriod` (weekly slots: seven
  day booleans, `opens`, `closes`, `access` open/card, optional `label`)
  and `LocationClosure` (inclusive date range + reason, overrides the
  week). Full per-date overrides (changed hours) are a to-do in
  `docs/to_fix.md`.
- `closes` earlier than (or equal to) `opens` means after midnight;
  `00:00` is midnight and shows as "24:00". `_end_after()` does this.
- Plain models, not `TranslatableMixin`: the English overlay installs on
  any model that declares `translated_fields` (`english_overlay.install`),
  so the children don't need a locale. Translated: `Location.name`, `note`,
  `warning`, `OpeningPeriod.label`, `LocationClosure.reason` (names too:
  user's choice). Adding a translated field means
  `manage.py update_translation_snapshot`.
- Seed: `seed_dev_data/opening_hours.py`, real hours from UiO pages
  (Nov 2026). Escape's bar is **Friday only** in the static data (user
  correction): other bar nights are Peoply events at Escape.
  `build_location()` is shared with the tests.

## Status logic: `location_status()`

- **Always Oslo time** (`SITE_TIMEZONE`). `settings.TIME_ZONE` is UTC, so
  `timezone.localdate()` would give the wrong day 00:00–01/02, exactly
  when the bar is open.
- Builds concrete `_Window`s for yesterday..+7 days (yesterday so a
  Friday 18–01 slot covers Saturday 00:30), plus event windows. State at a
  moment: closed if a closure covers that date; open if any open window
  covers it; card if only card windows; else closed.
- Next change: evaluate the state at every window start/end and the day
  after each closure, first one that differs. Exact, no minute stepping.
- `_when()`: no weekday for today, or for tomorrow before 05:00
  ("until 01:00", not "until Sat 01:00").
- Half price (`half_price_minutes`, Spiseri 30): "now" in the last N
  minutes before the place stops being open, "soon" in the N minutes
  before that. Shown as "Half price from 15:30" / pulsing "Half price now!".
- `show_parts` lists the slot labels (plus "Event" if `event_location`
  is set) as `Kafé | Bar | Event`, the active ones bold. Only shown while
  open.
- `opening_hours_now()` is the seam the view calls; a live source (the
  planned Escape API) would replace a place's status there.

## Events (Escape)

- `Location.event_location` matched case-insensitively against
  `EventPage.location` (user: Peoply stores "Escape" as the location). Live,
  not archived, `event_date` yesterday or today.
- An event counts as **open while it runs** (user's choice) and lights
  "Event" (also for bar nights from Peoply: user's choice, no guessing from
  titles). No `event_end_time` → runs until 01:00 the next night
  (`EVENT_DEFAULT_END`). An event without `event_time` is ignored.
- The line shows the running event ("Now: …") or the next one starting
  later today ("Today 19:00: …"), linked with `{% pageurl %}`.
- Caveat: `sync_peoply_events` stores `freeformAddress or locationName`.
  An Escape event whose Peoply address is filled in gets the street
  address, not "Escape", and won't match.

## Box

- Frame copies `.eventsbox_container` (user asked for the events box's
  style for side-column boxes). No JavaScript: the week is a native
  `<details>` per place.
- Places with `hours_unconfirmed` get an orange `*` and their `warning`
  as a footnote at the bottom of the box.
- Placement: `aside.home-sidecolumn`. Normal order opening hours, events,
  magazine; while the magazine is highlighted (temporary comment in
  `home_index.html`) it's magazine, opening hours, events.
- nb strings (`Åpent`, `Kort kreves`, `Stengt` use `msgctxt "opening
  hours"` because `Closed` already exists) were added to the .po by hand:
  `makemessages` rewrites ~1,700 lines. "Event" is "Arrangement" in nb.
