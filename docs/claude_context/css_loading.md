# How CSS is loaded — design rationale

Covers `templates/global_base.html`'s tiered CSS blocks, the partials under
`templates/css_links/` and `apps/ifi_home_app/templates/css_links/`.

## The rule

Every stylesheet is a `<link>` tag, in `<head>`, listed in a template
partial. **Never `@import`, and never a `<link>` in a partial that renders
in the body.** Both rules exist because each was violated once and each
produced the same visible bug: a flash of unstyled content, most obvious
as images rendering at full natural size before snapping into place.

## Why not a `<link>` in a body partial

`ifi_home_app`'s partials (`home_sidemenu.html`, `home_newsbar.html`,
`home_eventsbox.html` and friends) used to carry their own `<link>` tags.
Those partials are `{% include %}`d inside `{% block content %}`, so the
tags landed in `<body>` -- at one point 19 of the homepage's 22
stylesheets. A stylesheet reached partway down the body is not
render-blocking: the browser has already painted everything above it
unstyled and restyles when the sheet arrives.

It also meant duplicate loads, since `{% block extra_css %}` declared
inside separate included templates does not deduplicate across them --
`newsbar_layout.css`, `card_base.css` and `article_card.css` were each
fetched twice on the homepage.

## Why not `@import`

Replacing those body links with per-tier `.css` files full of `@import`
fixed the body problem and did **not** fix the flash.

The browser's preload scanner races ahead through the HTML and starts
downloading every `<link href>` it can see, but it cannot see inside a
`.css` file. An `@import` is therefore only discovered after the importing
file has downloaded and parsed -- two sequential round trips instead of
one parallel wave. That is inherent to `@import`; it cannot be tuned away.

The delay matters for any script that measures layout at startup (see
below): it pushed the stylesheets past the moment such a script measured.

Note `apps/account_app/static/css/account_base.css` and
`apps/study_app/static/css/study_base.css` still use `@import` (3 each).
They have not been migrated yet. They are lower risk because the
layout-critical files (`tokens`, `reset`, `elements`, `page_layout`) come
from the global tier, which is plain `<link>` tags -- but they should move
to partials when those apps adopt the tier blocks.

## Scripts that measure layout must wait for stylesheets

`DOMContentLoaded` does **not** wait for stylesheets. A script that calls
`getBoundingClientRect()` (or similar) then forces layout against
half-applied CSS; Firefox warns *"Layout was forced before the page was
fully loaded"*, and the result is a flash of unstyled content.

The former `static/js/nav_overflow.js` (removed when the header nav became
plain CSS, see `header.md`) solved this with a `stylesheetsReady()` promise:
resolve once every `link[rel="stylesheet"]` has a non-null `.sheet`,
listening for `error` as well as `load` so one 404 sheet can't block it
forever. Reuse that pattern for any future script that measures geometry
at startup, even though `<link>`s in `<head>` already make deferred
scripts wait in practice.

## Request count

Each leaf file is its own `<link>`, so a page carries 20-36 of them. That
is the same set of files `@import` was fetching, just discovered in one
parallel wave instead of two sequential ones -- strictly faster, not
slower. If the request count ever becomes a real problem the answer is
concatenation (e.g. `django-compressor`), not `@import`.
