"""The single source of truth for every default that BLOCK_STYLE_DEFAULTS
(block_style.py) and ArticleStyle's own field defaults (style.py) need to
agree on -- font sizes, header alignment, side padding, and the hero
image's own styling. Both files import these directly rather than each
hardcoding their own copy, which is what let them drift out of sync in
the first place (twice, for font-size and alignment, before this existed).

Deliberately separate from tokens.css's --font-size-h1..h6/--text-align-*
(site chrome: union/event page section headings, home page, navbar, etc.)
-- those govern plain template-rendered headings with no per-block
editing, a different system that should never need to interact with this
one.

Not everything in BLOCK_STYLE_DEFAULTS is here -- only entries that
genuinely have a second copy elsewhere in Python to drift out of sync
with (ArticleStyle's own fields). A plain block type's own "alignment":
"center" (heading, paragraph, image, ...) has no such second copy, so
there's nothing to centralize."""

ARTICLE_TYPOGRAPHY = {
    "paragraph": 1.2,
    "intro": 1.5,
    "title": 3,
    "meta": 0.9,
    "h2": 2,
    "h3": 1.7,
    "h4": 1.5,
    "h5": 1.3,
}

ARTICLE_ALIGNMENT = {
    "title": "center",
    "intro": "center",
    "meta": "center",
}

ARTICLE_SIDE_PADDING = {
    "header": 0,
    "hero_image": 0,
}

# hero_image_position (style.py) / "alignment" (BLOCK_STYLE_DEFAULTS) --
# same value, different field name on each side (position is the more
# accurate name for a hero image; "alignment" just matches every other
# block type's own key so _effective_heading_style-style code can treat
# it uniformly).
ARTICLE_HERO_IMAGE = {
    "position": "right",
    "width_rem": 18,
    "boxed": False,
    "box_color": "bg-light",
    "box_border_radius": 0.75,
    "shadow_enabled": True,
    "shadow_strength": 1,
}
