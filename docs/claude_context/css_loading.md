# How CSS is loaded — design rationale

Covers `templates/ifi_base.html`'s tiered CSS blocks, the partials under
`templates/css_links/` and `apps/ifi_home_app/templates/css_links/`, and
the stylesheet wait in `static/js/nav_overflow.js`.

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

The delay matters because of `nav_overflow.js` below: it pushed the
stylesheets past the moment that script starts measuring.

Note `apps/account_app/static/css/account_base.css` and
`apps/study_app/static/css/study_base.css` still use `@import` (3 each).
They have not been migrated yet. They are lower risk because the
layout-critical files (`tokens`, `reset`, `elements`, `page_layout`) come
from the global tier, which is plain `<link>` tags -- but they should move
to partials when those apps adopt the tier blocks.

## Why nav_overflow.js waits for stylesheets

`static/js/nav_overflow.js` measures the header with
`getBoundingClientRect()` to decide whether the nav needs compact labels.
It used to do that immediately on `DOMContentLoaded`, which does **not**
wait for stylesheets. Firefox reports this directly: *"Layout was forced
before the page was fully loaded. If stylesheets are not yet loaded this
may cause a flash of unstyled content."* Forcing layout against
half-applied CSS makes the browser lay out and paint that state, then
restyle once the real CSS lands.

It now waits via `stylesheetsReady()`, which resolves once every
`link[rel="stylesheet"]` has a non-null `.sheet` (a `<link>`'s `.sheet` is
populated only after its stylesheet loads and parses). It resolves on
`error` as well as `load` on purpose: a single 404 stylesheet must not
leave the nav stuck in its unmeasured state forever.

With all CSS as `<link>` in `<head>`, browsers already delay deferred
scripts until those sheets load, so this wait is belt-and-braces. Keep it
anyway -- it is what stops a future stylesheet added somewhere new, or an
`@import` creeping back, from quietly reintroducing the flash. Any other
script that measures geometry at startup needs the same treatment.

## Request count

Each leaf file is its own `<link>`, so a page carries 20-36 of them. That
is the same set of files `@import` was fetching, just discovered in one
parallel wave instead of two sequential ones -- strictly faster, not
slower. If the request count ever becomes a real problem the answer is
concatenation (e.g. `django-compressor`), not `@import`.
