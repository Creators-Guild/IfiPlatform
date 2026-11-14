# Opening hours box

Last updated: 2026-11-14

How the home page shows whether IFI's places (Ole-Johan Dahls hus, the
library, Ole-Johan Spiseri and Escape) are open right now. Read
[overview.md](../overview.md) first. The events it uses for Escape come
from the Peoply sync, see [events.md](events.md).

## What it is

- **Visitors** see a box in the side column with one line per place: a
  pill saying **Open**, **Card needed** (only open with a UiO card right
  now) or **Closed**, and when that changes, for example "until 18:00" or
  "card access from 05:00". The full week is behind a "Hours" toggle.
- **Admins** edit the places and their hours under Snippets → "Opening
  hours" in the Wagtail admin. English is added like for other snippets.
- The hours are typed in by hand. A live API for Escape is planned.
- The four places are added by migration `0162_opening_hours_places` on a
  database that has none, so production has them after the first deploy.
  Their English comes from the nightly DeepL run.

## Models

All in `models/opening_hours.py`:

| Model | What it holds |
| --- | --- |
| `Location` | A place: name, note (e.g. "Halvpris siste 30 min"), order, active, and the extras below |
| `OpeningPeriod` | A weekly time slot of a place: which days, opens, closes, open to everyone or card needed, an optional label (e.g. "Kafé", "Bar", "Kort + PIN") |
| `LocationClosure` | Days a place is closed, with a reason shown in the box (e.g. "Juleferie") |

A closing time earlier than the opening time means after midnight, so the
bar's 18:00–01:00 is one slot. 00:00 means midnight and shows as 24:00.

Extras on `Location`:

- **Hours not guaranteed** and **warning**: the place gets a `*`, and the
  warning is shown at the bottom of the box. Escape uses this, since it's
  run by volunteers.
- **Show parts**: shows the slot labels as "Kafé | Bar | Event", with the
  ones running now in bold.
- **Event location**: events whose location is exactly this (Escape:
  "Escape") count as open while they run, and the box shows today's event
  with a link. An event without an end time counts until 01:00.
- **Half price minutes**: shows "Half price from 15:30" and then "Half
  price now!" before closing. The Spiseri uses 30.

Times are always worked out in Oslo time, even though the server's
`TIME_ZONE` is UTC.

## The box on the home page

- The view calls `opening_hours_now()`, which returns the status of every
  active place. That function is where a live source would plug in later.
- Template: `templates/home/partials/openinghours/openinghours.html`.
  Styles: `static/css/06_components/home/home_openinghours.css`. The frame
  matches the events box. There is no JavaScript.
- It sits in the side column. Normally it comes first, then events, then
  the magazine box.

## Where to change things

| To change | Edit |
| --- | --- |
| Hours, notes, warnings | The "Opening hours" snippet in the Wagtail admin |
| How "open now" is worked out | `location_status()` in `models/opening_hours.py` |
| The box's look | the template and CSS above |
| Hours on a fresh local database | `management/seed_dev_data/opening_hours.py` (English) and migration `0162_opening_hours_places` (the places) |

Tests are in `tests/test_opening_hours.py`.

## Known gaps

- Only whole closed days, not changed hours on a date (for example shorter
  hours in the exam period). Listed in [to_fix.md](../../to_fix.md).
- An Escape event only matches if its location on the site says "Escape".
  The Peoply sync stores Peoply's street address instead when one is set.
