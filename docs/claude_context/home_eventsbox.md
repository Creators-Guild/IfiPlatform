# Homepage events box — design rationale

Last updated: 2026-09-23
Covers: ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_eventsbox.css, ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_eventsbox_event.css

Covers the homepage "This month at Ifi" box:
`home/partials/home_eventsbox.html` (the list, empty state, "See all events",
staff Peoply button) and `home/partials/home_eventsbox_event.html` (one event
row, included per event), styled by
`ifi_home_app/static/css/06_components/home/home_eventsbox.css` (the box) and
`home_eventsbox_event.css` (the row). The box's outer sizing/placement lives in
`05_objects/home_layout.css` (see `home_layout.md`), including
`align-self: start` so the box is as tall as its content instead of stretching
to the column beside it.

It's a compact list, not the `newsbar_layout.css` card grid, because it sits in
a narrow column.

## No JavaScript

Both expanders are native `<details>`: the extra union tags and the sub-event
list. The box loads no script of its own (`peoply_sync_button.js` is staff-only
and belongs to the sync button). Don't reintroduce `dropdown_menu.js` here.

`.home-eventsbox-more-unions` is `display: contents` so its `<summary>` ("+N")
and the extra tags lay out as part of the same wrapping `.home-eventsbox-unions`
flex row instead of forming a block below it. Collapsed content still hides
correctly (verified with JS disabled). When testing, use `checkVisibility()`,
not `getBoundingClientRect()` — a collapsed `<details>` keeps a box.

## Row layout

Events are grouped by date with `{% regroup upcoming_events by event_date %}`
(`home_eventsbox.html`): one `.home-eventsbox-day` section per date, with an
`<h3>` heading and the day's events under it. A row
(`.home-eventsbox-item`) is a two-column grid: the start time on the left
(`.home-eventsbox-time`; "All day" when there is none, the end date for a
multi-day event) and `.home-eventsbox-body` on the right — badges, title,
calendar link, union tags, sub-events, one per line.

Earlier versions used a wrapping flex row where five children set
`flex-basis: 100%` to force their own line, plus a stretched-link overlay
(`.home-eventsbox-title-link::after`) that made the whole row clickable and
forced `position: relative; z-index: 1` on every interactive child. Both are
gone: only the title is a link.

Sub-event names wrap instead of being truncated, which removed the
`min-width: 0` chain the ellipsis needed on three levels.

## Time tag

`EventPage.time_tag` (`event_models.py`) returns `"today"`, `"tomorrow"` or
`None` — at most one, nearest first. `"today"` reuses `is_happening_now`, so a
multi-day event running across today counts.

The pill sits on the day heading (`home_eventsbox.html`), taken from the first
event of the group, so it shows once per day rather than per row. Colours: today
filled green (`--color-success`), tomorrow filled turquoise.

There is no separate "Happening today" section any more — it repeated events
already listed below it, and `home_views.main_view` no longer builds
`happening_now_events`.

## Template details

- **Union tags must go through `.localized`.** A `PageChooserBlock` inside a
  StreamField is not translated by wagtail-localize (page references keep
  pointing at the source-locale page; see `handle_related_object_block()` in
  `wagtail_localize/segments/extract.py`). Without `entry.union.localized`, an
  English homepage links to the Norwegian union pages.
- **`event.all_related_unions`, not `event.related_unions`:** it rolls in every
  sub-event's unions too (docstring in `event_models.py`). A week-long event
  like Fadderuke tags unions on its individual days, not on itself.
- **Only the first 2 union tags show**, the rest behind the `+N` expander. 2
  rather than 3 because this column is narrow on a phone.
- **`event.highlighted_sub_events`** is today's sub-events if any, else the
  curated `is_highlighted` set. With none, the row shows a plain count
  (`.home-eventsbox-subcount`) instead of the expander.
- **The calendar link** renders only when `event.calendar_days.days` exists — an
  untimed-only event has nothing at the `#event-calendar` anchor.
- **"See all events"**: `home_views.main_view` caps the box at 6 events, and
  `home_eventsbox.css` hides everything past the 3rd day below 72rem.

## Queries

`sub_events`, `all_related_unions`, `highlighted_sub_events` and `calendar_days`
are `@cached_property` (`event_models.py`), so a row reading several of them
queries once per event rather than per access, and `sub_events.count` is free
once anything has iterated the queryset. Measured: the box costs ~19 EventPage
queries for 6 events; the homepage total (~236) is dominated by articles and
menus, so this box is not the place to optimise further.
