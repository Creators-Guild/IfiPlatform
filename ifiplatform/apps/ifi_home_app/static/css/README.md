# ifi_home_app CSS structure

This folder follows ITCSS: folders are ordered by cascade/specificity
(objects load before components), not by "which page uses this". Each
tier has its own subfolders grouping related files together instead of
one flat list. Lives directly under `css/`, not nested inside a
`styles/neon_style/` wrapper -- there's only ever one theme, so that
extra nesting added path length without adding organization.

```
01_objects/   -- layout patterns: page shells/scaffolding (one page-shape
                 concern per subfolder: article/, category/, event/, home/,
                 newsbar/, tool/, union/)
02_components/ -- reusable UI widgets, one subfolder per widget family
                 (cards/, article_toc/, article_editor/, event/,
                 home_eventsbox/, messageboard/, navbar/, category/,
                 union/, tool/), plus shared/ for cross-cutting base files
                 and small generic-utility rules used by more than one
                 widget
```

## Naming conventions

- A file is named after the component/selector it defines, not the
  template that happens to use it.
- `_page.css` is reserved for a page's own visual/content identity
  (typography, color, decorative treatment) -- `article_page.css`,
  `tool_page.css`, `union_page.css`, `event_page.css`, `category_page.css`.
  `_layout.css` is for genuine layout/positioning (flex, grid, structure,
  breakpoints) -- `home_layout.css`, `category_layout.css`,
  `newsbar_layout.css`. Never pick one word when a file is really both:
  `category_layout.css`/`category_page.css` and
  `home_layout.css`/`home_page.css` are each a deliberate split of what
  used to be one mixed file, so "how this is laid out" and "what this
  looks like" each read as one thing per file. A file only stays merged
  when its layout and visual properties are genuinely inseparable rule by
  rule (e.g. `event_page.css` has many selectors mixing `display`/`flex`
  with `color`/`border` on the very same rule -- splitting those apart
  property-by-property would read worse, not better, so it doesn't get a
  `_layout.css` counterpart).
- `_page`/`_layout` never applies outside `01_objects/` page shells -- a
  card, modal, or any other `02_components/` file keeps its own name
  regardless of which page renders it (`cards/article_card.css` is a card,
  not a page, even though only pages render it).
- A large file mixing unrelated concerns is split by concern into several
  small files under one subfolder, rather than kept as one long file (e.g.
  `article_toc.css` -> `article_toc/article_toc_trigger.css` +
  `article_toc_modal.css` + `article_toc_overlay.css`).
- A reusable widget carved out of a page shell (e.g. `union_page.css`'s
  member grid) belongs in `02_components/`, not alongside the page shell
  it was carved from -- `union/union_member_card.css` (the card grid) and
  `union/union_position_info.css` (its hover popover) are two separate
  components, not one file, since the popover is a distinct concern reused
  from the same `popover_base.css` pattern as `article_toc_overlay.css`.
- `02_components/shared/` holds two kinds of files: genuinely
  cross-component base files (`card_base.css`, `modal_base.css`,
  `popover_base.css` -- see their own file comments for exactly which
  declarations are shared and why some look-alike properties were
  deliberately left out), and small standalone utilities used by more than
  one page/component (`block_box.css`, `article_meta.css`,
  `translation_warning.css`).

## No bundler

There is no build step or manifest for this app's CSS -- every template
hardcodes its own `{% static 'css/<path>/<file>.css' %}` `<link>` tags.
Moving, renaming, or splitting a file here always means finding and
updating every template `<link>` tag that references its old path.

A shared base file (`card_base.css`/`modal_base.css`/`popover_base.css`) is
always linked *in addition to*, and *before*, the specific component
file(s) that use it, so the specific file can still override it.
`title_banner.css`'s `<link>` must come after `category_page.css`'s in
any template loading both -- see the comment in `title_banner.css` for why.
