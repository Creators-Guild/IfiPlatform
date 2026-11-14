# home_layout.css — design rationale

Last updated: 2026-11-13
Covers: ifiplatform/apps/ifi_home_app/static/css/05_objects/home_layout.css, ifiplatform/apps/ifi_home_app/static/css/05_objects/home_index_layout.css, ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_navbar_mobile.css

Covers the homepage grid (`home/home_index.html`), which lives in
`ifi_home_app/static/css/05_objects/home_index_layout.css` (loaded only on
the homepage). `home_layout.css` (loaded on every page using
`home_base.html`) now only holds `.maincontent`'s padding; the grid moved
out of it on 2026-09-23. Also covers `06_components/home/home_navbar_mobile.css`.
`06_components/home/home_eventsbox.css` holds the events box's card look;
its contents are covered in `home_eventsbox.md`, the magazine box in
`home_magazinebox.md`.

## The grid

`.home-layout .maincontent` is a named-area grid: `nav`, `shortcuts`, then
`content` (`#home-subcontent`: message board + suggestions row) beside
`details` (`aside.home-sidecolumn`: normally the opening hours box, the
events box, then the >OUTPUT magazine box; while the magazine is
highlighted it comes first, see the comment in `home_index.html`). Columns are `minmax(0, 1fr) auto` —
`minmax(0, …)` rather than plain `1fr` so the content column can shrink
below its content's min-content width instead of pushing the events box
off-screen (a plain `1fr` track has an `auto` minimum).

Main-column spacing (user, 2026-11-14: the boxes sat too close): the gap
between message board, news and Instagram is 4.5rem each ("way more"
than the first 2.5rem): `margin-top` on `.suggestions-row` (4rem, plus
the message board's 0.5rem bottom margin) and `.instagram_container`
(4.5rem).
Set outside the media queries, so it holds in both layouts. The news and
Instagram titles (both `.newsbar-heading`) sit *inside* their cards (user's
choice): on the homepage the card style is on `.newsbar_container`
(`home_newsbar.css`), not the article grid, and the Instagram `<h2>` is
inside `.home-instagram-card`. `#home-subcontent .newsbar-heading` gives
both the same margins inside the card (scoped so news headings on other
pages keep theirs).

`.home-sidecolumn` carries the placement the events box used to have
(`grid-area`, `align-self: start`, `max-width: 23rem`, `margin`); the boxes
stack inside it with a fixed gap. A grid row per box was rejected: with
the content column spanning both rows, a tall left column opens a gap
between the boxes. The covers' intrinsic width makes the column sit at its
23rem cap.

## Below 72rem: `#home-subcontent { display: contents }`

The layout goes single-column, and the goal order is message board, then
Events, then News/Articles — but in the DOM the events box comes after
`#home-subcontent` (which holds both `#msg-board` and `.suggestions-row`).
`display: contents` un-boxes `#home-subcontent` so its children become
direct grid items of `.maincontent`, letting `#msg-board` (`msg`) and
`.suggestions-row` (`suggestions`) be placed on either side of
`details` (the side column, so events then magazine). The Instagram feed (`.instagram_container`,
the last child of `#home-subcontent`) gets its own `instagram` area after
`suggestions`, so on phones it comes last. Their `grid-area` rules exist only inside this media query;
above 72rem they're ordinary children of `#home-subcontent`.

The `72rem` value is shared by eye with `home_eventsbox.css`
and `messageboard_slideshow.css` (plus
`messageboard.js`'s `MOBILE_QUERY`) — there's no shared variable between
plain CSS files. It's wider than the `45rem` breakpoint used elsewhere
because, with the events box beside it, the content column has already
lost the box's width plus margins long before the viewport is phone-sized.

## `home_navbar_mobile.css` (below 45rem)

The navbar's dropdowns open as a full-navbar-width panel: `.home-navbar`
gets `position: relative` and `.home-navbar .dropdown-menu` is forced to
`position: static`, so the absolutely-positioned `.drop-content` resolves
against the navbar rather than its own menu item — both are required for
`left: 0; right: 0` to mean "navbar width". `top: calc(100% + 0.75rem)`
pushes the panel below the side menu's icon box. Dropdowns whose menu slot
has "hide on mobile" (`.dropdown-menu--hide-mobile`, News/Info by default)
are hidden, and a menu group's short title (`.drop-option-full`/`-short`)
replaces its title.
`home_layout.css`'s `.home-navbar { padding-left: 3rem }` at the same
breakpoint belongs to this layout.
