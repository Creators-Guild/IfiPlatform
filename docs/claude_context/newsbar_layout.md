# newsbar_layout.css — design rationale

Covers `ifi_home_app/static/css/05_objects/newsbar/newsbar_layout.css` —
the auto-fit card grid shared by the homepage's "Suggested News"/
"Suggested Info Articles" sections and the article index/category pages'
"Suggested Articles" section.

## Heading truncation: ellipsis, not wrap, not shrink-to-fit

`.newsbar-heading--news`/`--articles` reserve room for exactly one line
(`white-space: nowrap; overflow: hidden; text-overflow: ellipsis`).
Reserving two lines up front left a permanent gap under whichever heading
only ever needed one, which was most of the time — this way the common
case (fits on one line) costs no extra space, and a too-long heading
truncates instead of wrapping and pushing the card grid down. A
JS-driven shrink-to-fit (scaling the font down instead of truncating) was
tried here and dropped — it looked jarring in practice, not worth the
added complexity.

## Why `grid-template-columns` uses `1fr`, not a fixed max card width

A *fixed* max (tried at both `26rem` and `30rem` before landing here) can
never fully avoid dead space: `auto-fit` only adds another column once
the container is wide enough for one more card at that max width, so at
any container width just *below* that threshold, whatever number of
cards already fit are stuck at their max size with the remaining leftover
width sitting empty beside them. Raising or lowering the max just moves
where that gap falls; it can't remove it.

`1fr` instead of a fixed `rem` removes it structurally: `auto-fit` still
decides *how many* columns fit using the minimum (`18rem`) as usual, but
every column that does fit then stretches to evenly fill 100% of the
container's width, with nothing left over at any width. The remaining
trade-off — a lone card in a very wide column growing quite large — is
handled separately: `.newsbar-layout .articlecard` caps the *card's* own
`max-width` (`40rem`, generously high so it only kicks in for genuinely
extreme cases) and centers it within whatever track it's given, instead
of capping the track itself the way the rejected fixed-max approach did.

## Why `align-items: start`, not grid's default `stretch`

Grid's own default (`align-items: stretch`) forces every card in a row to
match the tallest one, so a card with a short title/intro next to one
with a long, wrapping title/intro got stretched taller than its own
content needs — its image (`aspect-ratio: 8/5`, `article_card.css`)
stayed correctly proportioned regardless (that ratio is locked to width,
not whatever height the row handed it), but the *card* itself no longer
matched that shape once stretched. `start` lets each card size to its own
content instead, so width and height move together (the image's locked
ratio drives the card's actual shape) rather than height being set
independently by row-mates.

## `.newsbar-layout .articlecard`'s sizing: `height`/`aspect-ratio`/`width`

- **`height: auto`**: `.articlecard`'s own `height: 100%` (`article_card.css`)
  is for its *other* use inside an editor-set explicit-height body block —
  a no-op there until that explicit height exists, but within this grid
  the row's own resolved height counts as definite, so `100%` would still
  stretch the card to match it. `auto` here keeps that other usage
  untouched.
- **`aspect-ratio: 5 / 4`**: locks the *whole card's* shape (image + title
  + meta + intro together), not just the image (which already has its own
  `aspect-ratio: 8/5`) — so News and Info Articles cards render
  identically sized/shaped as long as their grid tracks are the same
  width, and neither column's cards end up a different shape just because
  one title happened to wrap differently. `5/4` (wider/shorter than a
  previous `1/1`) is close to the practical limit for this stacked
  image-then-text layout: the image alone already needs close to a full
  4/5-shaped card's height at this width range, leaving very little for
  text — a true 16:9 "TV" ratio wasn't achievable without cropping the
  image or dropping the intro entirely (the intro's own `line-clamp: 1`
  was already trimmed down from 2 lines to fit at all). Even at `5/4`,
  `overflow: hidden` (`article_card.css`) clips a little more than the
  "just a sliver" slack the previous `1/1` ratio left.
- **`min-height: 0`**: grid items get an "automatic minimum size" by
  default (same idea as flex items) that lets them grow past their own
  `aspect-ratio`-computed height to fit their content's min-content
  size — exactly what was making some cards taller than others despite
  the locked ratio above. `0` defeats that, so `aspect-ratio` is actually
  authoritative and `overflow: hidden` clips anything that doesn't fit,
  instead of the box just growing.
- **`width: 100%`**: load-bearing, not decorative. `justify-self: center`
  switches this item from grid's default stretch sizing to shrink-to-fit
  (`auto`) sizing, which computes the box's width from its *content's own*
  intrinsic size instead of its track — and a percentage width on a
  descendant (like `.articlecard img`'s own `width: 100%`, or this card's
  image crop via `aspect-ratio` + `object-fit` needing a definite width to
  crop within) can't be resolved during that computation, so it's ignored
  and the descendant falls back to its intrinsic size instead. An
  unusually large source image (e.g. a tall logo/crest asset) could then
  pull the card wider than its own track — overflowing the viewport on
  mobile, visually overlapping sibling cards on wide desktop grids — and
  its own crop into the usual landscape tile shape never applies either.
  `width: 100%` keeps this item's own sizing definite regardless of what
  it contains, so `max-width` is what actually does the capping, not an
  ambiguous content-driven computation.

## Mobile: dropping the `aspect-ratio` lock entirely

At `max-width: 480px`, `.newsbar-layout .articlecard` drops the base
rule's `aspect-ratio: 5/4` lock back to content-driven `height: auto`. An
expanded (non-`--list`) card's image+h3+meta+`.articlecard-intro` no
longer had room to actually fit inside that shrinking, width-derived box,
and `overflow: hidden` was clipping the intro rather than the card
growing to fit it. At this width the grid is effectively always a single
column anyway (`16rem` is close to the practical per-card minimum), so
there's rarely a row-mate left to visually match in the first place.
(`max-width: 40rem`/`justify-self: center` don't need resetting here — the
base rule's own `width: 100%` keeps them a no-op at any track narrower
than `40rem`, mobile included.)

## The 45rem `.articlecard--list` breakpoint

Matches `home_layout.css`'s own `45rem` breakpoint, where the home
page's two sections stack into a single column and drop to 4 visible
cards each — a narrower breakpoint here left a gap zone (480px–45rem)
where cards had already stacked/capped but weren't list-styled yet.

Collapsing to a list row is driven by `article_list_toggle.js` adding
`.articlecard--list` directly (default: every card past the first two,
previously hard-coded via `:nth-child` — now also toggleable per card via
the arrow button, see `article_card.css`'s `.articlecard-toggle`), reusing
the exact same class/look the "Show as list item" editor toggle already
produces instead of a second, separately maintained set of rules for what's
visually identical. `grid-column: 1 / -1` is the only thing this layout
needs to add on top — `.articlecard--list` alone doesn't know it's sitting
in a grid, so without it the item would keep its normal card-sized track
instead of spanning the full row like a list item.
