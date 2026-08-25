# event_calendar.css — design rationale

Covers `ifi_home_app/static/css/02_components/event/event_calendar.css` —
the week/day calendar grid shared by a single event page's sub-events
(`event_page.html`) and a union page's own weekly calendar
(`union_page.html`/`union_calendar_panel.html`, via `union_calendar.js`).

## `.union-calendar-nav`: fixed-width columns, not flex/1fr centering

The label's text (a date range) varies in width week to week. Flex +
`justify-content: center`, or a `1fr` center column, would shift the
prev/next arrows along with it — `1fr` especially, since it'd stretch to
the full width of `.union-calendar-section`, planting the arrows way out
at its edges, far from the label they control. `1.5rem 19rem 1.5rem` fixed
columns keep the arrows both close to the label and pinned in place
regardless of which week/locale is showing — `19rem` comfortably fits the
longest realistic label with room to spare (measured: nb's
"1. september - 7. september 2026" is ~17.6rem). `width: fit-content` +
`margin: auto` centers this fixed-size block within the wider section
instead of stretching to it.

## Why the union calendar overrides `--ec-hour-height`

`UnionPage.get_context` fixes a union's calendar to one hour range for its
whole semester (`event_models.py`'s `hour_range_for_events`, derived from
that union's own earliest/latest timed event that semester, `9:00`-`01:00`
fallback if it has none) rather than each week resizing around whatever
happens to fall in it. The default `3.75rem` (base `.event-calendar` rule)
is sized for a typical single event's narrower hour span, and would make
a semester-wide range (often most of a day, and mostly empty on any given
week) too tall — `.union-calendar-section .event-calendar` overrides it
to `2.75rem` instead.

## The single-event sub-events calendar's own width

Positions/sizes computed by `EventPage.calendar_days`. Sits outside
`.event-page-prose`'s 50rem reading column on purpose and left-aligned,
using the *page's* full given width (i.e. `.maincontent`'s,
`home_layout.css`) rather than a width sized for paragraph text — a
5-day-wide grid needs the room, unlike prose, so there's no cap here at
all. Narrower columns/day-header text just get more cramped the narrower
`.maincontent` actually is, same as the mobile shrinking further down
already handles. `--ec-hours` (`hour_count` from `calendar_days`) drives
every block's actual pixel height indirectly: `3rem` per hour
(`--ec-hour-height`) is the one place that ratio is set, and the day
column's own height is derived from it so a block's top/height
percentages (relative to that column) land on the right gridlines.

## `.event-calendar-block` vs `.event-calendar-block-inner`: why two boxes

`.event-calendar-block` is purely a positioning box — `top`/`height`/
`left`/`width` (inline style) are `EventPage.calendar_days`' computed
percentages, unmodified by anything else here. It deliberately holds none
of the visible styling itself: `margin` doesn't actually shrink an
absolutely-positioned box's own width/height (those stay exactly as
specified), it only shifts the box within the space `top`/`left`/`width`/
`height` already claim — a margin here would open a gap on the top/left
edges while the bottom/right edges keep overflowing past their gridline
by the same amount. `inset` on the nested absolutely-positioned
`.event-calendar-block-inner` is the one that actually resolves against
this box's real, already-computed pixel size, so it can shrink evenly on
all four sides — `position: absolute` on the outer box alone is enough
for it to be that inner child's containing block, no separate
`position: relative` needed.

## The "view whole week" modal

Fixed overlay + contained scroll + close mechanics modeled on
`messageboard_modal.css`'s `.messageboard-modal`, but the content itself
is the full grid (`event_calendar_grid.html`), scrolled HORIZONTALLY
exactly like the grid's own pre-existing mobile fallback — just with an
explicitly visible scrollbar and edge fade hints, since a silently-
scrollable area with an auto-hiding native scrollbar is exactly the "not
obvious it's scrollable" problem this feature exists to fix. Not
media-query-gated itself: only ever opened from
`.event-calendar-view-whole-week`, which is CSS-hidden outside mobile, so
it's inert everywhere else regardless.

`.event-calendar-modal-scroll .event-calendar`'s `width: max-content` lets
the row grow past the panel's own width instead of being squeezed back
down to fit it, which is what actually creates the horizontal overflow to
scroll — the grid's own `.event-calendar-header-day`/`-day` rules (under
the `45rem` breakpoint) already lay it out at a fixed per-day width, which
inside the modal is exactly the layout wanted (all days side by side,
scrollable); it just needs to never collapse to one day the way
`.event-calendar--paged` does, which it won't, since this copy of the
grid never receives that class (`event_calendar.js` only ever pages the
inline section's own grid).

The left/right "more content this way" fade hints
(`.event-calendar-modal-fade-left`/`-right`) are direct children of
`.event-calendar-modal-panel` (not `.event-calendar-modal-scroll`), so
they stay fixed at the panel's own edges regardless of horizontal scroll
position — same reasoning as `messageboard_modal.css`'s
`.messageboard-modal-fade` being a sibling of its scroll area rather than
a child of it. Visibility is toggled via JS (`event_calendar.js`'s
`updateFades()`, mirroring `messageboard.js`'s `updateFade()`) from
`scrollLeft`/`scrollWidth`/`clientWidth`, re-checked on scroll, resize,
and modal open.

## Mobile full-screen modal takeover

True full-screen takeover on phones for the "view whole week" modal,
rather than the smaller centered card it uses above the `45rem`
breakpoint. At 100% width/height the panel IS the whole visible modal
(the dark `.event-calendar-modal` backdrop behind it has no edges left
showing), so its own background has to carry the "dark, see-through to
the page behind" look itself — the desktop card's opaque `--color-bg`
(meant to read as a solid card) would otherwise hide the site completely
instead. Text/backgrounds that assumed a light card underneath (day
headers, hour labels, the sticky hour rail, gridlines) get overridden
alongside it so they stay legible against dark instead of going
dark-on-dark.
