# global_base.html — design rationale

Covers `ifiplatform/templates/global_base.html`. Its tiered CSS blocks are
documented separately in [css_loading.md](css_loading.md).

## The `?v=6` on the favicon links

Every favicon `<link>` in the `<head>` of `global_base.html` (`favicon.svg`,
`favicon.ico`, `favicon-32.png`, `favicon-180.png`) ends in `?v=6`.

Browsers cache favicons unusually aggressively. They often ignore a normal
reload and even a hard refresh, and only fetch the icon again once its URL
changes. The query string is ignored by the server but makes the URL new to
the browser, so bumping the number is what forces a stale cached icon to
update.

When the favicon image itself changes, bump the number on all four links
together (e.g. `?v=6` → `?v=7`). Do not remove the query string as cleanup.
