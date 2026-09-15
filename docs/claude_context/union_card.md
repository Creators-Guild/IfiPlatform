# union_card.css — design history

Covers `ifi_home_app/static/css/06_components/cards/union_card.css`.

## Why the mobile breakpoint is 45rem, not 480px

`45rem`, not the `480px` this used to be pinned to — matches the
breakpoint every other mobile treatment on a page `union-card` can appear
on already uses (`event_calendar.css`'s calendar/day-paging,
`article_list_toggle.js`, `dropdown_menu.js`, ...). At the old, narrower
`480px`, a page like an event's "Involved Unions" section
(`event_page.html`) would already be showing its *other* content in
mobile layout well before `union-card` followed suit — e.g. at 600-700px
wide, the week-calendar above it had already switched to single-day
mobile view while these cards were still sitting in full desktop grid
mode right below it, visibly inconsistent on the same page.
