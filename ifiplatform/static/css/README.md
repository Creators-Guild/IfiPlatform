# Global CSS structure

- One global static folder (`ifiplatform/static/`, this one) shared
  sitewide, plus one per-app static folder (`ifiplatform/apps/<app>/static/`)
  for that app's own CSS -- see each app's own `static/css/README.md`.
- Try to avoid long files with lots of scrolling. Instead separate into
  new, more specific files.

## Structure of files: ITCSS (Inverted Triangle CSS)

Folders are ordered by cascade/specificity, so load order follows the
numbering. The numbers are the canonical ITCSS layer positions, so a
number means the same layer here and in every app's own tree:

```
01_settings/    # Variables, tokens (colors, spacing, fonts)
                # 02 = Tools (mixins/functions) -- N/A, no preprocessor
03_generics/    # Reset, normalize, box-sizing
04_elements/    # Bare HTML tags (h1, a, p)
05_objects/     # Layout patterns (container, grid)
06_components/  # UI components (card, nav, button)
                # 07 = Utilities/overrides -- none written yet
```

None should share the same number. The gaps at 02 and 07 are deliberate:
they hold those layers' canonical positions open, so adding a utilities
layer later means creating `07_utilities/` rather than renumbering
everything below it.

A per-app tree only has files in some of these layers (usually just
objects and components) -- it keeps these same numbers and simply has no
folder for the layers it doesn't need.

## How stylesheets reach a page: one block per tier

`ifi_base.html` declares an empty block per tier, in cascade order. A
template fills only its own tier, so it can never drop the tier above it:

```html
{% include "css_links/global.html" %}        {# global, every page #}
{% block app_css %}{% endblock %}      {# one partial per app #}
{% block section_css %}{% endblock %}  {# one per page family #}
{% block page_css %}{% endblock %}     {# one page only, rare #}
{% block extra_head %}{% endblock %}   {# non-CSS: meta, preloads, JS #}
```

Each tier includes exactly one **template partial** holding the `<link>`
tags for that tier, in cascade order. The global one is
`templates/css_links/global.html`; per-app ones live in that app's
`templates/css_links/` (see `apps/ifi_home_app/` for worked
examples). Partial names are namespaced by app directory because Django
merges every template directory into one namespace, so a bare
`css/article.html` would collide the moment a second app added one.

Three rules:

- **Never use `@import`.** A partial lists `<link>` tags instead. The
  browser's preload scanner races ahead through the HTML and starts
  downloading every `<link href>` it can see, but it cannot see inside a
  `.css` file -- so an `@import` is only discovered after the importing
  file has downloaded and parsed. That costs an extra round trip, and it
  delays the stylesheet past the point where scripts start measuring the
  page, which is what produces a flash of unstyled content. See
  `docs/claude_context/css_loading.md`.
- **Never put a `<link>` in a partial that renders in the body.** These
  CSS partials are included in `<head>`, which is the whole point. A
  stylesheet reached in the body isn't render-blocking -- the browser
  paints everything above it unstyled, then restyles when the sheet
  lands. Images are the obvious tell, flashing at full natural size.
- **A partial lists leaf files only, never another partial.** Nesting
  them would put the tiers' load order back out of one place.

Load order within a tier is the `<link>` order in that partial, so an
ordering constraint between two files gets written down once there
instead of being a trap in every template that loads both.

There's no bundler or manifest here -- paths are hardcoded, so moving,
renaming or splitting a file means updating every `<link>` that
references its old path. If the number of requests ever becomes a real
problem, the answer is concatenation (e.g. `django-compressor`), not
`@import`.


## Structure within files: BEM (Block Element Modifier)

Example:

```css
/* Block */
.card { }

/* Element */
.card__title { }
.card__image { }

/* Modifier */
.card--featured { }
.card__title--large { }
```
