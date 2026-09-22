# home_eventsbox_*.css — design rationale

Covers the homepage "This month at Ifi" box
(`home/partials/home_eventsbox.html`), styled by
`ifi_home_app/static/css/06_components/home/`:
`home_eventsbox_list.css`, `home_eventsbox_live.css`,
`home_eventsbox_subevents.css`, `home_eventsbox_mobile.css`. The box's
outer sizing/placement lives in
`05_objects/home_layout.css`; its card look in `home_eventsbox_card.css`
(see `home_layout.md`). It's a compact bulleted list, not the
`newsbar_layout.css` card grid, because it lives in a narrow column;
`.eventsbox_container`'s own padding already provides horizontal padding,
so `.home-eventsbox-list` adds none.

## Stretched link + separately clickable children

`.home-eventsbox-item` is a `<div>`, not an `<a>`, so union tags can be
their own links without nesting `<a>` in `<a>`. Whole-row clicking comes
from `.home-eventsbox-title-link::after` (`position: absolute; inset: 0`)
covering the row — `position: relative` on `.home-eventsbox-item` is its
containing block and must stay.

Every other interactive child must sit above that overlay with
`position: relative; z-index: 1`, or its clicks fall through to the event
link: `.home-eventsbox-union-tag`, `.home-eventsbox-unions-toggle`,
`.home-eventsbox-calendar-link`, `.home-eventsbox-subevents-toggle`, and
`.home-eventsbox-subevents-list a`. `.home-eventsbox-subcount` has no
href and intentionally stays under the overlay.

Hover: `.home-eventsbox-item:hover` lifts the row 1px (same convention as
`.articlecard`); hovering a child already counts as hovering the row, so
no `:has()` is needed. `.home-eventsbox-union-tag:hover`'s own
`translateY(-1px)` stacks on top, nudging the tag slightly further.

## Own-line children: `flex-basis: 100%`

The row is `display: flex; flex-wrap: wrap`. `.home-eventsbox-title`,
`.home-eventsbox-unions`, `.home-eventsbox-subcount`,
`.home-eventsbox-calendar-link`, `.home-eventsbox-subevents` (and
`event_badges.css`'s `.event-peoply-note`) use `flex-basis: 100%` to drop
onto their own line; removing it makes them trail inline after the date.

## `min-width: 0` chain for ellipsis truncation

Sub-event links (`.home-eventsbox-subevents-list a`,
`.home-eventsbox-live-sublist a`) are `white-space: nowrap` +
`text-overflow: ellipsis`. That only engages if every flex ancestor can
shrink: flex items default to `min-width: auto`, so without
`min-width: 0` on `.home-eventsbox-subevents` *and* on the links
themselves (the list is itself a column flexbox), one long name pushes
`.eventsbox_container` wider than its column and produces a horizontal
scrollbar instead of truncating. Same for `.home-eventsbox-live-sublist`.

`.home-eventsbox-subevents-toggle` is `inline-flex` with `flex-wrap: wrap`
and `max-width: 100%` for the same reason: an inline-flex's items (count
text + `-toggle-hint`) never wrap relative to each other by default, so a
long translation would overflow.

## Toggles

- **Union tags** (`.home-eventsbox-union-tag--extra`): tags past the
  first 2 are hidden until `.home-eventsbox-unions` gets `.is-open`, set
  on click on every device by `dropdown_menu.js`'s `setupTapToggle`.
  Plain `display` toggle (inline pills in a wrapping row, nothing to
  animate). Deliberately no `:hover` reveal — hovering the row to read the
  date opened them too easily. `-toggle-more`/`-toggle-close` swap the
  "+N"/"Close" label off the same `.is-open`.
- **Sub-events** (`.home-eventsbox-subevents-list`): collapsed with
  `max-height: 0; opacity: 0; overflow: hidden`, not `display: none` — a
  real height is what lets the `max-height` transition animate, and
  staying in normal flow means expanding just pushes later events down.
  Opened by `.is-open` (JS) or, on `(hover: hover) and (pointer: fine)`
  devices only, by `:hover`. The open `max-height: 20rem` must stay larger
  than the tallest real list or items get clipped. The caret
  (`-toggle::after`, a CSS triangle) flips on the same conditions.

## "Happening now" (`home_eventsbox_live.css`)

`.home-eventsbox-live` (`EventPage.is_happening_now`) sits above the list.
The label uses `--color-cta`, not `--color-accent`: the latter is
`.event-type-badge--social`'s color and would read as "social event"
rather than "live". The label is a block heading on its own line, since
several events can be live at once. `.home-eventsbox-live-sublist` shows
`EventPage.live_sub_events` always expanded, same border-left indent as
the sub-events list.

## Mobile collapse (`home_eventsbox_mobile.css`)

The `72rem` breakpoint must match `home_layout.css`'s stacking breakpoint
(and `messageboard.md`'s); no shared variable exists between plain CSS
files, so keep them in sync by eye.

- Below 72rem only the first 4 `li`s of `.home-eventsbox-list` show
  (`li:nth-child(n+5)` hidden); the live callout stays fully visible. This
  keeps the stacked box short — no `max-height` needed. The rest is reached
  via "See all events" (`.home-eventsbox-view-all`, the events index). A
  former "See more events" full-screen expand (`.is-expanded`,
  `home_eventsbox.js`) was removed as redundant with that overview.
