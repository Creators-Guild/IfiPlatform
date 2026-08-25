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

## .union-layout / .union-main / .union-sidebar

`.union-main` and `.union-sidebar` are deliberately NOT a grid/flex row
sharing a track. Two things were tried and reverted before this:

1. A grid row with `max-width` on `.union-main` directly, as the
   `minmax(0, 1fr)` item. The browser sized the whole *track* around that
   max-width, pushing `.union-sidebar`'s fixed `16rem` column off-screen —
   `max-width` on a grid item can feed back into the track's own sizing.
2. A real grid row again, this time with max-width moved onto
   `.union-main`'s children instead of the item itself (which avoids the
   track-sizing bug above) — this got side-by-side working down to a much
   smaller breakpoint, but `.union-main`'s content ended up centered
   *within its own column* rather than against the full page, which reads
   as shifted left of true center whenever the sidebar shows. Explicitly
   rejected: full-page centering (ignoring the sidebar) is the actual
   requirement here, not "centered in whatever space is left."

The current design instead makes `.union-main` a plain block, centered
against `.union-layout`'s full width with zero awareness of
`.union-sidebar`. Above the breakpoint, `.union-sidebar` is taken out of
flow (`position: absolute`, anchored via `position: relative` on
`.union-layout`) so it truly cannot feed back into `.union-main`'s
centering math. Below the breakpoint it sits in normal flow — it comes
*before* `.union-main` in `union_page.html` specifically so the stacked
order puts it above "Purpose", not dumped after every section once it
overflows into normal flow.

`text-align: center` is safe on `.union-main` only because of this split —
it's a plain block, not a row item that could feed the text width back
into shared track sizing.

### The breakpoint is currently being calibrated live, not derived

Mathematically, avoiding overlap with this design needs roughly
`2 * (.union-main half-width + .union-sidebar width + gap)` of
`.union-layout` width to break even:
`60rem / 2 + 16rem + 2rem gap ≈ 96rem`. A previous version of this page
used `115rem` (that derived minimum plus a deliberate buffer). The
breakpoint is currently `60rem` -- known to be too small (will overlap) --
set that way on purpose so the actual overlap point can be found by eye in
the browser and adjusted up from there, rather than trusting the formula
alone. Don't "fix" this number back up to the derived ~96rem without
checking first — it's mid-calibration.

## .union-sidebar-row

Contact and Members boxes sit side by side and wrap on their own (no extra
breakpoint) once there's no room for both — relevant above the current
breakpoint where `.union-sidebar` is only `16rem` wide, not below it where
`.union-sidebar` matches `.union-main`'s `60rem` column width.
