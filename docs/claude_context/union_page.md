# union_page.css / union_page.html — layout rationale

Covers `ifi_home_app/static/css/05_objects/union/union_page.css`
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

### Where the 80rem breakpoint came from

Mathematically, avoiding overlap with pure full-page centering needs
roughly `2 * (.union-main half-width + .union-sidebar width + gap)` of
`.union-layout` width to break even: `60rem / 2 + 16rem + 2rem gap ≈ 96rem`.
A previous version of this page used `115rem` (that derived minimum plus
a deliberate buffer). This time the number was tuned live in the browser
instead of computed up front — deliberately started too small (`60rem`,
guaranteed overlap) and raised in steps (`70rem` → `80rem`) until the
overlap was gone, landing below the ~96rem derived minimum. That gap
between "tuned" and "derived" is exactly what the push zone below exists
to cover.

## The 80rem–104rem push zone

Between `80rem` (where `.union-sidebar` starts floating) and the ~96rem
derived break-even point above, pure full-page centering isn't reliably
safe yet. Rather than let `.union-main`/`.union-header` overlap
`.union-sidebar` in that range, `.union-page` (their shared parent —
*not* `.union-layout`) gets `padding-right: 18rem` there, so both
re-center within the same narrower remainder and stay lined up with each
other — the same `margin: auto` centering they already had, just now
solving against a narrower canvas.

That padding doesn't move `.union-sidebar` on its own — `right: 0`
(set in the `min-width: 80rem` block) resolves against `.union-layout`'s
own padding box, which `.union-page`'s padding doesn't touch directly.
But `.union-layout` itself, as a plain block filling `.union-page`'s
content box, physically shrinks by that same `18rem` — which would drag
`.union-sidebar`'s anchor `18rem` left of `.union-page`'s true right edge
along with it. `right: -18rem` in this same breakpoint block compensates,
pushing back out by exactly the space `.union-page` reserved, landing
`.union-sidebar` back at the true right edge — same visual position as
outside this range. **Keep the `18rem` padding-right and the `-18rem`
right-offset equal if either one changes.**

104rem is just past where the derived ~96rem minimum clears with a small
buffer — above it, `.union-page` drops the padding and full-page centering
is safe on its own again.

## .union-sidebar-row

Contact and Members boxes sit side by side and wrap on their own (no extra
breakpoint) once there's no room for both — relevant above `80rem` where
`.union-sidebar` is only `16rem` wide, not below it where `.union-sidebar`
matches `.union-main`'s `60rem` column width.
