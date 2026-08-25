# article_page.css — design history

Covers `ifi_home_app/static/css/01_objects/article/article_page.css`.

## Why title/intro/meta each got their own alignment control

`.article-page`'s own `--content-alignment` (consumed via `text-align`)
used to also govern the title/intro/meta group — they inherited it rather
than having their own value. Editors wanted the title and intro alignable
separately from each other (and from the body), so each got its own
control (`ArticlePage.title_alignment`/`intro_alignment`/`meta_alignment`,
`--title-alignment`/`--intro-alignment`/`--meta-alignment`). `--content-alignment`
is now only a fallback for anything with no alignment control of its
own — rare, since most block types (heading/paragraph/image/multi_column)
set `text-align` explicitly on themselves, which always wins over this
inherited value regardless of specificity.

## Why the mobile reset breakpoint is 45rem, not 480px

The `@media (max-width: 45rem)` block that resets editor-picked side
padding/alignment/font-size back to plain defaults used to fire at `480px`
instead — narrower than `45rem` (720px), the breakpoint every other mobile
treatment on the site uses (`event_page.css`, `union_card.css`,
`article_multicolumn.css`, `article_image.css`, `dropdown_menu.js`, ...).
A visitor in that 480px–45rem gap got none of this reset: editor-picked
side padding/alignment/font-size on the article header stayed at their
desktop values on a phone-width screen, which is exactly the "large
padding/centered alignment reads badly this narrow" problem the reset
exists to prevent. Moved to `45rem` to match the rest of the site and
close that gap.
