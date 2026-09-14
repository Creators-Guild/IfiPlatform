# ifi_home_app CSS structure

This folder follows ITCSS: folders are ordered by cascade/specificity
(objects load before components), not by "which page uses this". The
numbers are the canonical ITCSS layer positions used sitewide (see
`ifiplatform/static/css/README.md`), which is why this tree starts at 05
-- it simply has no files in the layers below it. Each tier has its own
subfolders grouping related files together instead of one flat list.
Lives directly under `css/`, not nested inside a `styles/neon_style/`
wrapper -- there's only ever one theme, so that extra nesting added path
length without adding organization.

```
05_objects/   -- layout patterns: page shells/scaffolding (one page-shape
                 concern per subfolder: article/, category/, event/, home/,
                 newsbar/, tool/, union/)
06_components/ -- reusable UI widgets, one subfolder per widget family
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
- `_page`/`_layout` never applies outside `05_objects/` page shells -- a
  card, modal, or any other `06_components/` file keeps its own name
  regardless of which page renders it (`cards/article_card.css` is a card,
  not a page, even though only pages render it).
- A large file mixing unrelated concerns is split by concern into several
  small files under one subfolder, rather than kept as one long file (e.g.
  `article_toc.css` -> `article_toc/article_toc_trigger.css` +
  `article_toc_modal.css` + `article_toc_overlay.css`).
- A reusable widget carved out of a page shell (e.g. `union_page.css`'s
  member grid) belongs in `06_components/`, not alongside the page shell
  it was carved from -- `union/union_member_card.css` (the card grid) and
  `union/union_position_info.css` (its hover popover) are two separate
  components, not one file, since the popover is a distinct concern reused
  from the same `popover_base.css` pattern as `article_toc_overlay.css`.
- `06_components/shared/` holds two kinds of files: genuinely
  cross-component base files (`card_base.css`, `modal_base.css`,
  `popover_base.css` -- see their own file comments for exactly which
  declarations are shared and why some look-alike properties were
  deliberately left out), and small standalone utilities used by more than
  one page/component (`block_box.css`, `article_meta.css`,
  `translation_warning.css`).

## Entry points (template partials, not CSS files)

Templates never link a leaf file from `05_objects/` or `06_components/`
directly. They include one partial per tier, and the partial holds the
`<link>` tags -- see `ifiplatform/static/css/README.md` for the
block-per-tier mechanism and the three rules that come with it, the first
of which is **never use `@import`**.

The partials live in this app's template tree, not here beside the CSS:

```
apps/ifi_home_app/templates/css_links/
  base.html                 -- app tier: what EVERY page here needs,
                               included once in home_base.html
  home_index.html           -- section tier: one per page family.
  article.html                 category.html covers both
  category.html                article_index_page and
  studentunion_category.html   article_category_page, whose
  union.html                   stylesheet needs are identical.
  event.html
  event_index.html
  tool.html
  article_editor.html       -- page tier: editor mode only, included
                               behind {% if can_edit_style %} so ordinary
                               visitors never download it
```

Ordering constraints live in those partials now, written once, instead of
being something every template has to get right:

- A shared base file (`card_base.css`/`modal_base.css`/`popover_base.css`)
  is linked *before* the specific component file(s) that use it, so the
  specific file can still override it. Never link a base file *after*
  those components -- it would win instead. This is why
  `popover_base.css`/`modal_base.css` sit in `category.html` and
  `studentunion_category.html` unconditionally, even though only editor
  mode uses them, rather than in `article_editor.html`.
- `title_banner.css` is linked after `category_page.css` -- see the
  comment in `title_banner.css` for why.
- `translation_warning.css` is linked last in every section partial:
  `05_objects/article/article_page.css` also styles
  `.translation-warning`, and this one has to win.
- In `base.html`, `06_components/sidemenu.css` comes after
  `home_layout.css` for the same reason -- both style `.sidemenu`.

No build step or manifest -- paths are hardcoded, so moving, renaming or
splitting a file means updating every `<link>` that references it.
