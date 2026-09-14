# title_banner.css — design rationale

Covers `ifi_home_app/static/css/06_components/category/title_banner.css`.

## What `.title-banner` is and where its config comes from

Optional decorative banner behind the title — `CategoryPage`/
`ArticleIndexPage`'s own `PageBannerStyle` (see `BannerStyleMixin` in
`article_models.py`), edited on-page via editor mode
(`banner_style_panel.html`/`banner_style.js`), not a Wagtail `FieldPanel`.
Flat color, not a gradient/image — `banner_color`/`--dot-color` and the
title's own color are all editor-chosen hex values (inline style, see
`article_category_page.html`/`article_index_page.html`), each with a
fixed fallback when left blank. Width/height default to `auto` (plain
full-width block, height driven by its own padding/content) —
`banner_width_rem`/`banner_height_rem` set an explicit inline width/height
instead when chosen (`0`/blank stays `auto`, see `PageBannerStyle`'s own
comment). `title_banner.js` scatters the actual dot pattern (a handful of
soft circles) into this at load.
