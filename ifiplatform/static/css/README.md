# Global CSS structure

- One global static folder (`ifiplatform/static/`, this one) shared
  sitewide, plus one per-app static folder (`ifiplatform/apps/<app>/static/`)
  for that app's own CSS -- see each app's own `static/css/README.md`.
- Try to avoid long files with lots of scrolling. Instead separate into
  new, more specific files.

## Structure of files: ITCSS (Inverted Triangle CSS)

Folders are ordered by cascade/specificity, so load order follows the
numbering:

```
01_generics/    # Reset, normalize, box-sizing
02_settings/    # Variables, tokens (colors, spacing, fonts)
03_elements/    # Bare HTML tags (h1, a, p)
04_objects/     # Layout patterns (container, grid)
02_components/  # UI components (card, nav, button)
```

(`02_components` shares its number with `02_settings` rather than sitting
at `05` -- this project's own numbering doesn't follow the textbook ITCSS
layer count exactly, since there's no separate settings/generic/elements
split needed per-app the way the global tree has one. Follow what
actually exists over a stricter canonical scheme.)

`base.css` (this folder's own entry point, linked from `ifi_base.html`)
pulls in the sitewide files via `@import`, in that same numeric order:

```css
@import "01_generics/reset.css";
@import "02_settings/tokens.css";
@import "03_elements/elements.css";
@import "04_objects/page_layout.css";
@import "02_components/back_to_link.css";
/* ...one @import per 02_components file actually needed sitewide */
```

Page/component-specific CSS isn't pulled in through `base.css` -- it's
linked directly per-template instead:

```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/<path>/<file>.css' %}">
```

There's no bundler or manifest here -- every template hardcodes its own
`<link>` tag path, so moving/renaming/splitting a file always means
finding and updating every template that references its old path.

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
