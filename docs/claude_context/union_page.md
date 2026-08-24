# union_page.css / union_page.html — layout rationale

Covers `ifi_home_app/static/css/styles/neon_style/02_components/union_page.css`
and `ifi_home_app/templates/info_articles/pages/union_page.html`.

## .union-header

Logo, title, and the open/closed badge stack vertically, centered, matching
`.union-main`'s reading-column width so the two line up visually. Both
`.union-header` and `.union-header-text` need `flex-direction: column` —
not just the outer one — because `.union-header-text` on its own is a flex
row by default, and its children (an inline-block `h1` and the badge span)
would sit side by side if there were room, even with the outer element
already stacked.

## .union-layout / .union-main / .union-sidebar: independent layouts, not a shared row

`.union-main` and `.union-sidebar` are deliberately NOT a grid/flex row
sharing a track. That was tried twice and broke twice:

1. `max-width` directly on `.union-main` as a `minmax(0, 1fr)` grid item
   made the browser size the whole track around that max-width, pushing
   `.union-sidebar`'s fixed `16rem` column off-screen.
2. Rebuilding the row with flexbox (`flex: 1` / `flex: 0 0 16rem`) to fix
   the above broke centering again.

The working design instead makes `.union-main` a plain block, centered
against `.union-layout`'s full width with zero awareness of
`.union-sidebar`. Above the `115rem` breakpoint, `.union-sidebar` is taken
out of flow (`position: absolute`, anchored via `position: relative` on
`.union-layout`) so it truly cannot feed back into `.union-main`'s
centering math. Below `115rem` it sits in normal flow — it comes *before*
`.union-main` in `union_page.html` specifically so the stacked order puts
it above "Purpose", instead of landing after every section once it
overflows into normal flow.

`text-align: center` is safe on `.union-main` only because of this split —
it's a plain block, not a row item that could feed the text width back
into shared track sizing.

### Where 115rem comes from

`.union-main` centers against `.union-layout`'s *full* width regardless of
the sidebar, so avoiding overlap needs roughly
`2 * (.union-main half-width + .union-sidebar width + gap)` of
`.union-layout` width just to break even:
`60rem / 2 + 16rem + 2rem gap ≈ 96rem` minimum. `.union-layout` itself is
somewhat narrower than the viewport (the sidemenu rail + `.maincontent`'s
own side padding — see `home_layout.css`). `115rem` clears the 96rem
break-even point with real margin, chosen deliberately generous ("stack
earlier rather than cut it close") after two tighter breakpoints both
overlapped/overflowed in testing.

## .union-sidebar-row

Contact and Members boxes sit side by side and wrap on their own (no extra
breakpoint) once there's no room for both — relevant above 115rem where
`.union-sidebar` is only 16rem wide, not below it where `.union-sidebar`
matches `.union-main`'s 60rem column width.
