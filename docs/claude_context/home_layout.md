# home_layout.css — design rationale

Covers `ifi_home_app/static/css/05_objects/home/home_layout.css` (and
`06_components/home/home_eventsbox_card.css`, which holds the look
of the same `.eventsbox_container` selector).

## `.eventsbox_container`'s width: a `clamp()`, not a fixed value

The events box is a narrower column (a compact bulleted list, not a card
grid, so it doesn't need to grow the way the card columns do) that sizes
to its own content height — `align-items: flex-start` on `.content-row`
already does that by default, so there's no `align-self: stretch`
override needed. `clamp(18rem, 20vw, 30rem)` gives it a share of extra
space on a wide screen (independent of whether the card columns are using
theirs or not — `newsbar_layout.css`'s own card-width cap is what gives
*them* first claim on extra space) instead of always sitting at exactly
the same width regardless of how much room the page actually has.

The `18rem`/`30rem` floor/ceiling were raised from an earlier `16rem`/`26rem` —
that ceiling was cramped enough that a full row of union tags or the
"N sub-events" toggle text routinely needed more room than it had (see
the `min-width: 0` fixes in `home_eventsbox_subevents.css`). `flex-shrink: 1`
(was `0`) lets it give a little back if the row is ever genuinely tight,
though the `72rem` breakpoint below already stacks it to full-width
before that would normally matter.

The row's overall height still comes from `.content-main` (the taller
sibling in practice, once it has a few news/article cards), so the space
below a short events box stays reserved/blank rather than being handed
back to `.content-main` — it just isn't filled by this box's own
border/background any more. `overflow-y: auto` is a safety net, not the
normal case: nothing currently constrains the box's content from
exceeding `.content-row`'s height, but it's harmless either way.
`overflow-x: hidden` is required alongside it, not decorative — setting
only `overflow-y` to a non-visible value makes the CSS overflow spec force
`overflow-x` to `auto` too (the same quirk noted in `dropdown_menu.js`'s
own comment re: `.nav_links`), which was producing a horizontal scrollbar
on any content a hair too wide instead of wrapping the way
`home_eventsbox_list.css` intends.

## Where the 72rem breakpoint comes from

Events drops below `.content-main` entirely well before News/Articles run
out of room — its own, wider breakpoint rather than sharing
`.suggestions-row`'s `45rem` one further down, because the two aren't
measuring the same available width. `.suggestions-row`'s `45rem` was
calibrated against `.content-main` having the *whole* row to itself; once
Events sits beside it, `.content-main` permanently loses ~19rem (`18rem`
flex-basis + `1rem` gap) before either column gets a single px. Sharing
one breakpoint meant that from `45rem` up to roughly here, both columns
AND the events box were all forced into the same row at once — exactly
the "squeezed, doesn't fill available width" problem this fixes.
`72rem` is sized so `.content-main` still has ~45rem to itself
(comfortable room for two 22rem card columns + gap) even with Events
still present: ~3.75rem (collapsed `.sidemenu`) + 4rem (`.maincontent`
padding) + 45rem (`.content-main`) + 19rem (Events + gap) ≈ 72rem.

## Stacked layout (below 72rem): `display: contents` + `order`

`display: contents` un-boxes `.content-main` — its own children
(`.messageboard`, `.suggestions-row`) become direct flex items of
`.content-row` alongside `.eventsbox_container`, instead of staying nested
inside a separate flex container of their own. That's what lets the
`order` properties reach across what used to be that boundary: the goal
is Message board, then Events, then News/Articles (not "Events last,
after everything else in `.content-main`", which is what plain DOM order
would give once stacked). Box-level properties on `.content-main` itself
(`flex`, `min-width`, its own `display: flex`) all stop applying once it's
`display: contents`, but none of them were meaningful once it no longer
generates a box anyway.

The `.content-main > .suggestions-row` selector (not
`.content-row > .suggestions-row`) matters here: `display: contents`
above only stops `.content-main` from generating its own box, it doesn't
change the DOM, so `.suggestions-row`'s actual parent for
selector-matching purposes is still `.content-main`. `order` itself works
fine across that boundary (a flex item's `order` is about its position
among the flattened box tree's siblings, not the DOM) — it's specifically
the child-combinator match that needs the real DOM relationship.

## `.eventsbox_container.is-expanded`: the full-screen takeover

Full-screen-ish takeover once `.home-eventsbox-more` is tapped
(`home_eventsbox.html`/`.js`) — same "tap to see everything, scrollable"
card look as `.messageboard-modal-panel` (`messageboard_modal.css`:
border, radius, shadow), just expanding this box itself in place
(`position: fixed`) instead of cloning its content into a separate
dialog, since the list has real interactive state of its own (union tag
toggles, sub-event toggles, links) that a clone would have to duplicate.

`inset: 0.5rem` rather than a flush `0` — small enough to still read as
"fills the screen", but enough of a gap for the border/radius/shadow to
actually show as a floating card rather than being clipped flat against
the viewport edge. Deliberately not capped to a small centered dialog the
way `.messageboard-modal-panel` is (`max-width: 26rem`) — more screen for
an events *list* to actually be useful pays off more than it does for a
single message's few paragraphs. `z-index: 1000` matches every other
full-page overlay on the site (`.messageboard-modal`, `.tool-lightbox`,
`.event-calendar-modal`).
