# messageboard_slideshow.css / messageboard_modal.css — design rationale

Covers `ifi_home_app/static/css/02_components/messageboard/messageboard_slideshow.css`
and `messageboard_modal.css`.

## Why the mobile breakpoint is 72rem, and what changes there

`72rem`, not a narrower phone-only width — matches `home_layout.css`'s own
stacking breakpoint (`.content-row` goes `flex-direction: column` there,
and `.eventsbox_container` switches to its own compact/collapsed mobile
look at the same width, `home_eventsbox_mobile.css`). Below that
breakpoint the message board sits directly above the events box in a
single narrow column, so it needs this same compact treatment throughout
that whole range — not just once at an actual phone width, or the two
would visibly mismatch (the message board still desktop-sized while
Events had already gone compact) anywhere from 480px up to 72rem.
`messageboard.js`'s own `MOBILE_QUERY` has to stay in sync with this
value by eye (same as `home_eventsbox_mobile.css`'s own reference to the
72rem breakpoint it doesn't own — no shared variable exists between plain
CSS files).

Below 72rem: there isn't room for the centered dots and the right-aligned
signature to share a row without colliding, so both become normal flow
instead of absolutely positioned, stacking (signature, then the
prev/dots/next controls row) as regular block content below the body text
rather than floating on top of it or each other. Height switches from a
fixed size to `auto` + `max-height`: a short message stays compact instead
of leaving a big empty gap, while a long one can grow up to the cap
before its body text starts scrolling/clamping internally.
