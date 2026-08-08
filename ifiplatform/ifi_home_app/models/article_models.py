"""Models for Wagtail-managed information articles: categories, index and article pages."""

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.conf import settings
from django.utils import timezone
from wagtail.models import Locale, Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock
from wagtail import blocks

# !Wagtail has no views and don't need any!

HEX_COLOR_VALIDATOR = RegexValidator(
    r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    "Enter a valid hex color code, e.g. #ff8800 or #f80.",
)

# shared fixed palette + custom-hex-fallback pattern, used anywhere a block
# needs a background/border color (image boxes, the box block).
COLOR_CHOICES = [
    ("bg-light", "Light"),
    ("turq", "Turquoise"),
    ("pink", "Pink"),
    ("purple", "Purple"),
    ("black", "Black"),
    ("custom", "Custom (hex code)"),
]



def _get_translation_progress(page):
    """Returns (total, translated) string-segment counts for the wagtail-localize
    Translation of `page` into its own locale, or None if there's no such record
    (e.g. it was never submitted for translation via wagtail-localize)."""
    try:
        from wagtail_localize.models import Translation
    except ImportError:
        return None
    translation = (
        Translation.objects.filter(
            source__object_id=page.translation_key,
            target_locale_id=page.locale_id,
            enabled=True,
        )
        .order_by("-created_at")
        .first()
    )
    if translation is None:
        return None
    return translation.get_progress()


def _page_needs_translation(page):
    """True if `page` itself is untranslated: either it's still an untouched
    alias auto-created by locale synchronisation (mirroring another locale's
    content rather than having its own), or a real translation that
    wagtail-localize considers incomplete. `alias_of` is unambiguous about
    which side of a locale pair is the placeholder, unlike comparing text
    between the two pages."""
    if page.alias_of_id is not None:
        return True
    progress = _get_translation_progress(page)
    return progress is not None and progress[1] < progress[0]


class TranslationWarningMixin:
    """Adds `needs_translation` to context: True if this specific page is
    untranslated (an alias placeholder, or an incomplete translation)."""

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["needs_translation"] = _page_needs_translation(self)
        return context


def article_image_block():
    """A single image with an optional caption, shared by the top-level
    'image' block and the image option inside multi-column text. Layout
    and box styling (alignment/width/side padding/border/background) are
    deliberately not part of this block at all -- they live only in
    ArticleBlockStyle, edited on-page via editor mode
    (article_block_style.js), with BLOCK_STYLE_DEFAULTS as the fallback
    when no override exists yet (see _effective_block_styles() and
    _effective_box_style()). Wagtail's job here is just the image itself
    and its caption, not how it looks on the page."""
    return blocks.StructBlock(
        [
            ("image", ImageChooserBlock()),
            (
                "alt_text",
                blocks.CharBlock(
                    required=False,
                    help_text="Accessible description. Leave blank to use the image's own title.",
                ),
            ),
            ("caption", blocks.CharBlock(required=False)),
        ],
        icon="image",
    )


def article_styled_text_block():
    """A rich text block, structurally just a wrapper around the text with
    no fields of its own beyond that -- kept as its own block type (rather
    than added to the existing plain 'paragraph' block, whose value is just
    a bare RichText string) purely as the *signal* that this particular
    paragraph opts into per-block on-page styling: article_body_blocks.html
    only gives styled_text blocks the "Edit block style" trigger, alignment/
    font-size/side-padding come from ArticleBlockStyle (edited via editor
    mode, article_block_style.js), with BLOCK_STYLE_DEFAULTS as the
    fallback when no override exists yet -- see _effective_block_styles().
    A plain 'paragraph' just inherits the article's own global style
    instead, with no per-block override available. Changing 'paragraph'
    itself to carry this distinction would need a data migration to
    convert every existing paragraph across every article; this way
    existing content is untouched, editors opt into the new block going
    forward."""
    return blocks.StructBlock(
        [
            ("text", blocks.RichTextBlock()),
        ],
        icon="pilcrow",
        label="Styled Text",
    )


def article_card_block():
    """Embeds another ArticlePage as a homepage-style card (hero image,
    title, author/date meta, truncated intro) -- lets an editor recommend a
    related article inline, in the body or inside a multi_column column,
    reusing the exact same article_card.html partial as the homepage/
    newsbar/article-index card grids rather than duplicating that markup.
    A function (not a shared instance) for the same reason article_image_
    block()/article_styled_text_block() are: Wagtail block instances carry
    per-use bookkeeping and aren't safe to reuse across multiple StreamField/
    StreamBlock definitions (this is used at both the top level and inside
    multi_column's column content)."""
    return blocks.StructBlock(
        [
            (
                "article",
                blocks.PageChooserBlock(
                    page_type="ifi_home_app.ArticlePage",
                    required=True,
                    help_text="The article to recommend.",
                ),
            ),
        ],
        icon="doc-full",
        label="Article Card",
    )


def _body_content_blocks():
    """The block types available at the top level of an article body --
    factored out so the 'box' block below can offer the exact same set
    inside itself (any of the *other* blocks, per its own docstring),
    without a box being nestable inside another box. Returns fresh block
    instances each call, same reason article_image_block() and
    article_styled_text_block() are functions rather than shared instances:
    Wagtail block instances carry per-use bookkeeping and aren't safe to
    reuse across multiple StreamField/StreamBlock definitions."""
    return [
        (
            "heading",
            blocks.StructBlock(
                [
                    ("text", blocks.CharBlock()),
                    (
                        "level",
                        blocks.ChoiceBlock(
                            choices=[
                                ("h2", "Level 1"),
                                ("h3", "Level 2"),
                                ("h4", "Level 3"),
                                ("h5", "Level 4"),
                            ],
                            default="h2",
                            label="Subsection level",
                            help_text=(
                                "How deep this heading nests in the article's "
                                "structure -- drives both its size and its "
                                "indentation in the table of contents. Stored as "
                                "an HTML heading tag (h2-h5) under the hood, but "
                                "shown here as a plain nesting depth since the "
                                "actual tag doesn't matter to editors."
                            ),
                        ),
                    ),
                ]
            ),
        ),
        ("paragraph", blocks.RichTextBlock(icon="pilcrow")),
        ("styled_text", article_styled_text_block()),
        (
            "multi_column",
            # Each column's own relative weight, the gap between columns, and
            # the block's own side padding all live only in ArticleBlockStyle
            # (edited on-page via editor mode, article_block_style.js), with
            # BLOCK_STYLE_DEFAULTS as the fallback when no override exists yet
            # -- see _effective_block_styles(). column_alignment stays here
            # since it's a structural/layout choice (vertical positioning,
            # a different axis entirely from left/right weighting) with no
            # on-page equivalent -- moving it out would make it uneditable.
            blocks.StructBlock(
                [
                    (
                        "columns",
                        blocks.ListBlock(
                            blocks.StructBlock(
                                [
                                    ("title", blocks.CharBlock(required=False)),
                                    (
                                        "content",
                                        blocks.StreamBlock(
                                            [
                                                ("text", blocks.RichTextBlock()),
                                                (
                                                    "styled_text",
                                                    article_styled_text_block(),
                                                ),
                                                ("image", article_image_block()),
                                                ("article_card", article_card_block()),
                                            ],
                                            required=False,
                                        ),
                                    ),
                                ]
                            ),
                            min_num=1,
                            max_num=4,
                            label="Column",
                        ),
                    ),
                    (
                        "column_alignment",
                        blocks.ChoiceBlock(
                            choices=[
                                ("top", "Top"),
                                ("center", "Center"),
                                ("bottom", "Bottom"),
                            ],
                            default="top",
                            help_text=(
                                "Only matters if columns end up different heights "
                                "(more text, a bigger letter size, or an image in "
                                "one but not another). Decides where the shorter "
                                "column's empty space goes: below it (Top), split "
                                "above and below (Center), or above it (Bottom)."
                            ),
                        ),
                    ),
                ],
                icon="placeholder",
                label="Multi-column Text",
            ),
        ),
        ("image", article_image_block()),
        ("article_card", article_card_block()),
    ]


def _iter_toc_entries(body_stream):
    """Recursively walks a body StreamValue yielding (level, text) pairs for
    anything the table of contents should link to: top-level headings, and
    multi_column column titles (treated as h3s, since they're a smaller
    heading-like label rather than a real 'heading' block -- see
    article_body_blocks.html, which gives both an id built the same way
    (slugify(text)), so these pairs line up with the actual anchors on the
    page."""
    for block in body_stream:
        if block.block_type == "heading":
            yield block.value["level"], block.value["text"]
        elif block.block_type == "multi_column":
            for column in block.value["columns"]:
                if column.get("title"):
                    yield "h3", column["title"]


# Default values for each on-page-editable style field, per block type --
# the *sole* source of these values for heading/styled_text/image/
# multi_column blocks, since none of them carry style fields of their own
# any more (see article_image_block()/article_styled_text_block()/
# _body_content_blocks()'s own docstrings for why: styling lives only in
# ArticleBlockStyle, edited on-page via editor mode). Used as the fallback
# in _effective_block_styles() below whenever a block has no
# ArticleBlockStyle override yet, and to power the "Reset to default"
# button in the on-page block style panel (article_block_style.js, via
# ArticlePage.get_context()). article_header/hero_image are the exception
# -- those are plain ArticlePage fields (title_font_size, hero_image_
# position, etc.), which still carry their own real default= and aren't
# read from here for rendering, only for the reset button.
BLOCK_STYLE_DEFAULTS = {
    "heading": {
        "alignment": "left",
        "font_size": 1.5,
        "side_padding": 0,
        # blank -- no override means "leave the text color alone" (inherit
        # the page's normal text color) rather than a real color of its own.
        "text_color": "",
        "text_custom_color": "",
    },
    "styled_text": {
        "side_padding": 1,
        "alignment": "left",
        "font_size": 1,
        "text_color": "",
        "text_custom_color": "",
    },
    "image": {"alignment": "center", "width_rem": 20, "side_padding": 0},
    # an image's own title (alt_text) and caption text -- independent of
    # each other and of the figcaption's own box (see "image_caption"
    # below) -- matches article_image.css's own plain defaults (both
    # inherit the figcaption's 0.85rem/center, .image-title's own
    # font-weight:bold stays a fixed CSS rule, not editable here).
    "image_title": {"alignment": "center", "font_size": 0.85, "side_padding": 0, "text_color": "", "text_custom_color": ""},
    "image_caption_body": {"alignment": "center", "font_size": 0.85, "side_padding": 0, "text_color": "", "text_custom_color": ""},
    "multi_column": {"side_padding": 1, "gap": 2, "column_weight": 1},
    "article_header": {
        "side_padding": 0,
        "title_alignment": "left",
        "title_font_size": 2,
        "intro_alignment": "left",
        "intro_font_size": 1,
        "meta_alignment": "left",
        "meta_font_size": 0.9,
    },
    "hero_image": {"alignment": "right", "width_rem": 18, "side_padding": 0},
    # not a StreamField block or per-block override -- there's only ever one
    # table-of-contents icon on the page (ArticlePage.toc_icon_size).
    "toc_icon": {"toc_icon_size": 1.3},
    # box styling is available on every body block (heading/styled_text/
    # image/multi_column) and independently on each multi_column sub-column
    # (keyed by that column's own stable id -- see _effective_block_styles())
    # -- the on-page replacement for the old Wagtail 'box' block, which
    # wrapped a group of blocks in one shared container instead. That
    # grouping capability is gone (each block/column now gets its own
    # independent box), a deliberate tradeoff for keeping box styling
    # entirely out of Wagtail. "padding" is the space between the box's
    # border and its own content; "margin" is the space between the box and
    # whatever comes before/after it on the page.
    "box": {
        "enabled": False,
        "border_width": 0.125,
        "border_color": "black",
        "border_custom_color": "",
        "border_visible": True,
        "radius": 0.75,
        "bg_color": "bg-light",
        "bg_custom_color": "",
        "padding": 1,
        "margin": 0,
    },
}
# a multi_column column's own title offers "the same options as a heading"
# (see _effective_heading_style()), so it shares that same defaults dict --
# not a separate copy that could drift out of sync with it.
BLOCK_STYLE_DEFAULTS["column_title"] = BLOCK_STYLE_DEFAULTS["heading"]


def _effective_box_style(override):
    """The effective box style (border/background/radius/padding/margin)
    for one block/column: its ArticleBlockStyle override where set, falling
    back field-by-field to BLOCK_STYLE_DEFAULTS['box'] otherwise. Shared by
    every block type in _effective_block_styles() below (and by each
    multi_column sub-column), since box styling works identically
    everywhere it's offered."""
    defaults = BLOCK_STYLE_DEFAULTS["box"]
    return {
        "enabled": (
            override.box_enabled if override and override.box_enabled is not None else defaults["enabled"]
        ),
        "border_width": (
            override.box_border_width
            if override and override.box_border_width is not None
            else defaults["border_width"]
        ),
        "border_color": (
            override.box_border_color
            if override and override.box_border_color
            else defaults["border_color"]
        ),
        "border_custom_color": (
            override.box_border_custom_color
            if override and override.box_border_custom_color
            else defaults["border_custom_color"]
        ),
        "border_visible": (
            override.box_border_visible
            if override and override.box_border_visible is not None
            else defaults["border_visible"]
        ),
        "radius": (
            override.box_radius if override and override.box_radius is not None else defaults["radius"]
        ),
        "bg_color": (
            override.box_bg_color if override and override.box_bg_color else defaults["bg_color"]
        ),
        "bg_custom_color": (
            override.box_bg_custom_color
            if override and override.box_bg_custom_color
            else defaults["bg_custom_color"]
        ),
        "padding": (
            override.box_padding if override and override.box_padding is not None else defaults["padding"]
        ),
        "margin": (
            override.box_margin if override and override.box_margin is not None else defaults["margin"]
        ),
    }


def _effective_heading_style(override, defaults):
    """The effective font_size/side_padding/alignment/box for one heading-
    shaped piece of text: any ArticleBlockStyle override for it, falling
    back field-by-field to `defaults` (BLOCK_STYLE_DEFAULTS['heading'] for
    an actual heading block, but reused as-is for anything else that should
    offer "the same options as a heading" -- currently also a multi_column
    column's own title, see _effective_block_styles() below)."""
    return {
        "font_size": (
            override.font_size if override and override.font_size is not None else defaults["font_size"]
        ),
        "side_padding": (
            override.side_padding
            if override and override.side_padding is not None
            else defaults["side_padding"]
        ),
        "alignment": (
            override.alignment if override and override.alignment else defaults["alignment"]
        ),
        "text_color": (
            override.text_color if override and override.text_color else defaults["text_color"]
        ),
        "text_custom_color": (
            override.text_custom_color
            if override and override.text_custom_color
            else defaults["text_custom_color"]
        ),
        "box": _effective_box_style(override),
    }


def _effective_block_styles(body_stream, overrides_by_block_id):
    """Recursively walks a body StreamValue (or a column's own nested
    content, same block types) yielding {block_id: {...}} for every
    heading/styled_text/image/multi_column block: any ArticleBlockStyle
    override for it, falling back to BLOCK_STYLE_DEFAULTS where there's no
    override (these blocks carry no style fields of their own to fall back
    to instead -- see BLOCK_STYLE_DEFAULTS' own docstring above), plus a
    'box' entry from _effective_box_style() on every one of them. Each
    multi_column's own sub-columns also get their own entry, keyed by that
    column's own stable id (a ListBlock item id, same idea as a top-level
    block's own id -- see ListValue.bound_blocks in Wagtail), containing
    only 'box' (columns have no other style of their own). Kept as plain
    dicts rather than touching block.value.font_size etc. directly in
    templates, so the "was this overridden by the on-page panel" logic
    lives in one place. Same recursion shape as _iter_toc_entries."""
    styles = {}
    for block in body_stream:
        block_id = str(block.id)
        override = overrides_by_block_id.get(block_id)
        if block.block_type in ("heading", "styled_text"):
            styles[block_id] = _effective_heading_style(override, BLOCK_STYLE_DEFAULTS[block.block_type])
        elif block.block_type == "image":
            defaults = BLOCK_STYLE_DEFAULTS["image"]
            styles[block_id] = {
                "alignment": (
                    override.alignment if override and override.alignment else defaults["alignment"]
                ),
                "width_rem": (
                    override.width_rem
                    if override and override.width_rem is not None
                    else defaults["width_rem"]
                ),
                "side_padding": (
                    override.side_padding
                    if override and override.side_padding is not None
                    else defaults["side_padding"]
                ),
                "box": _effective_box_style(override),
            }
            # the image's own title (alt_text, also shown visibly -- see
            # article_image_block.html) and caption are boxable together as
            # one unit (its own <figcaption>, wrapping both), independent of
            # the image's own box above -- synthesized id, same pattern as a
            # multi_column column's own title below.
            caption_id = f"{block_id}-caption"
            caption_override = overrides_by_block_id.get(caption_id)
            styles[caption_id] = {
                "side_padding": (
                    caption_override.side_padding
                    if caption_override and caption_override.side_padding is not None
                    else 0
                ),
                "box": _effective_box_style(caption_override),
            }
            # the title/caption text themselves (alignment/font size/side
            # padding/color) are further independent of each other and of
            # the figcaption's own box above -- two more synthesized ids,
            # each reusing _effective_heading_style() like a column's own
            # title does (its own "box" entry is simply unused here, the
            # figcaption's own box above is the only one that applies).
            title_text_id = f"{block_id}-cap-title"
            styles[title_text_id] = _effective_heading_style(
                overrides_by_block_id.get(title_text_id), BLOCK_STYLE_DEFAULTS["image_title"]
            )
            caption_text_id = f"{block_id}-cap-body"
            styles[caption_text_id] = _effective_heading_style(
                overrides_by_block_id.get(caption_text_id), BLOCK_STYLE_DEFAULTS["image_caption_body"]
            )
        elif block.block_type == "multi_column":
            defaults = BLOCK_STYLE_DEFAULTS["multi_column"]
            own_weights = [defaults["column_weight"]] * len(block.value["columns"])
            override_weights = override.column_weights if override else None
            styles[block_id] = {
                "side_padding": (
                    override.side_padding
                    if override and override.side_padding is not None
                    else defaults["side_padding"]
                ),
                "gap": override.gap if override and override.gap is not None else defaults["gap"],
                "column_weights": (
                    override_weights
                    if override_weights and len(override_weights) == len(own_weights)
                    else own_weights
                ),
                "box": _effective_box_style(override),
            }
            for bound_column in block.value["columns"].bound_blocks:
                column_id = str(bound_column.id)
                column_override = overrides_by_block_id.get(column_id)
                styles[column_id] = {
                    "side_padding": (
                        column_override.side_padding
                        if column_override and column_override.side_padding is not None
                        else 0
                    ),
                    "box": _effective_box_style(column_override),
                }
                # a column's own title (plain text on the column struct
                # itself, not a real block with a Wagtail-assigned id of its
                # own) gets the same font_size/alignment/box options as an
                # actual heading block -- synthesized id so it can still use
                # the same ArticleBlockStyle override table.
                title_id = f"{column_id}-title"
                styles[title_id] = _effective_heading_style(
                    overrides_by_block_id.get(title_id), BLOCK_STYLE_DEFAULTS["heading"]
                )
                styles.update(
                    _effective_block_styles(bound_column.value["content"], overrides_by_block_id)
                )
    return styles


def _split_categories_by_season(categories):
    """Split live categories into (main, seasonal) lists, seasonal filtered to currently-active ones."""
    main = [c for c in categories if not c.is_seasonal]
    seasonal = [c for c in categories if c.is_seasonal and c.is_currently_active]
    return main, seasonal


def get_section_index(section):
    """The site's live ArticleIndexPage for `section` ('info_articles' or 'news'),
    in the active locale."""
    return (
        ArticleIndexPage.objects.live()
        .filter(locale=Locale.get_active(), section=section)
        .first()
    )


def get_section_categories(section):
    """Currently visible categories in `section` flagged for menu display."""
    categories = CategoryPage.objects.live().filter(
        locale=Locale.get_active(), show_in_menu=True
    )
    return [c for c in categories if c.is_visible and c.category_section == section]


# Current tree: ArticleIndexPage -> ArticleCategory -> ArticlePage


# Model for Articles (yeah, they are all so f*ing long, don't ask...)
class ArticlePage(TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """A single article page, published under a CategoryPage."""

    template = "info_articles/pages/article_page.html"  # custom path

    intro = RichTextField(blank=True)
    # featured image
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    HERO_POSITION_CHOICES = [
        ("left", "Left"),
        ("center", "Center"),
        ("right", "Right"),
    ]

    hero_image_position = models.CharField(
        max_length=20,
        choices=HERO_POSITION_CHOICES,
        default="right",
    )
    hero_image_width_rem = models.FloatField(
        default=18,
        help_text="Width, in rem.",
    )
    hero_image_side_padding = models.FloatField(
        default=0,
        help_text="Left/right padding, in rem (0 = none).",
    )

    hero_image_title = models.CharField(
        max_length=250,
        blank=True,
        help_text="Shown under the image, above the caption. Leave blank for none.",
    )
    hero_image_alt = models.CharField(
        max_length=250,
        blank=True,
        help_text="Accessible description of the image, for screen readers -- not shown visibly. Leave blank to use the image's own title.",
    )
    hero_image_caption = models.CharField(max_length=250, blank=True)
    hero_image_boxed = models.BooleanField(
        default=False,
        help_text="Draw a border/box around the image, title and description.",
    )

    BOX_COLOR_CHOICES = [
        ("bg-light", "Light"),
        ("turq", "Turquoise"),
        ("pink", "Pink"),
        ("purple", "Purple"),
        ("black", "Black"),
        ("custom", "Custom (hex code)"),
    ]

    hero_image_box_color = models.CharField(
        max_length=20,
        choices=BOX_COLOR_CHOICES,
        default="bg-light",
        help_text="Box background color (only applies when 'boxed' is enabled).",
    )
    hero_image_box_custom_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[HEX_COLOR_VALIDATOR],
        help_text="Hex code, e.g. #ff8800. Only used when color is set to 'Custom'.",
    )
    hero_image_box_border_radius = models.FloatField(
        default=0.75,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Box corner rounding, in rem (0 = square corners). Only applies when 'boxed' is enabled.",
    )
    # metadata
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    published_date = models.DateField(null=True, blank=True)
    show_on_homepage = models.BooleanField(
        default=True,
        help_text="Whether this article can be suggested on the homepage (newsbar/articles bar).",
    )

    content_side_padding = models.FloatField(
        default=0,
        help_text=(
            "Left/right padding around the whole article body, in rem (0 = "
            "none). Applies on top of the site's own layout padding, and "
            "stacks with any per-block side padding inside it."
        ),
    )

    CONTENT_ALIGNMENT_CHOICES = [
        ("left", "Left"),
        ("center", "Center"),
        ("right", "Right"),
    ]

    content_alignment = models.CharField(
        max_length=20,
        choices=CONTENT_ALIGNMENT_CHOICES,
        default="left",
        help_text=(
            "Default alignment for any plain heading/paragraph content in "
            "the article body. Blocks with their own alignment option "
            "(styled text, images, multi-column) override this "
            "individually -- as does the title/intro/meta block above the "
            "body, which has its own separate alignment controls."
        ),
    )

    TITLE_ALIGNMENT_CHOICES = CONTENT_ALIGNMENT_CHOICES

    title_alignment = models.CharField(
        max_length=20,
        choices=TITLE_ALIGNMENT_CHOICES,
        default="left",
        help_text="Alignment for the article title.",
    )
    title_font_size = models.FloatField(
        default=2,
        help_text="Font size for the article title, in rem. Independent from the body's own font size.",
    )
    intro_alignment = models.CharField(
        max_length=20,
        choices=TITLE_ALIGNMENT_CHOICES,
        default="left",
        help_text="Alignment for the intro paragraph.",
    )
    intro_font_size = models.FloatField(
        default=1,
        help_text="Font size for the intro paragraph, in rem. Independent from the body's own font size.",
    )
    meta_alignment = models.CharField(
        max_length=20,
        choices=TITLE_ALIGNMENT_CHOICES,
        default="left",
        help_text="Alignment for the byline/date meta row.",
    )
    meta_font_size = models.FloatField(
        default=0.9,
        help_text="Font size for the byline/date meta row, in rem. Independent from the body's own font size.",
    )

    header_side_padding = models.FloatField(
        default=0,
        help_text=(
            "Left/right padding around the title/meta/intro block, in rem "
            "(0 = none). Independent from the body's own side padding."
        ),
    )

    content_font_size = models.FloatField(
        default=1,
        help_text=(
            "Default font size for the body, in rem. Title, intro and meta "
            "have their own separate font size controls. Per-block font "
            "size (styled text) overrides this individually."
        ),
    )

    content_bg_enabled = models.BooleanField(
        default=False,
        help_text="Override the article body's default background color.",
    )
    content_bg_color = models.CharField(
        max_length=20,
        choices=COLOR_CHOICES,
        default="bg-light",
        help_text="Background color (only applies when the override above is enabled).",
    )
    content_bg_custom_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[HEX_COLOR_VALIDATOR],
        help_text="Hex code, e.g. #ff8800. Only used when color is set to 'Custom'.",
    )

    toc_icon_size = models.FloatField(
        default=1.3,
        help_text=(
            "Size of the table-of-contents icon (the circular \"contents\" "
            "button next to the title), in rem. The button's own circle "
            "grows and shrinks along with it."
        ),
    )

    # allows for mutiple sections of one of these types:
    body = StreamField(
        _body_content_blocks(),
        use_json_field=True,
    )

    # Deliberately no FieldPanel for the styling fields (content_side_padding/
    # content_alignment/content_font_size/content_bg_enabled/content_bg_color/
    # content_bg_custom_color/toc_icon_size, title_alignment/title_font_size,
    # intro_alignment/intro_font_size, meta_alignment/meta_font_size,
    # header_side_padding, hero_image_position/hero_image_width_rem/
    # hero_image_side_padding) -- those fields still exist and still store
    # real values (used whenever there's no more specific value set), but
    # they're edited on-page via editor mode (article_block_style.js /
    # article_quick_style.js), not in Wagtail. Wagtail's job here is
    # structure and content; editing the same value from both places would
    # be confusing, since the on-page save always wins in the end anyway.
    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("hero_image_title"),
        FieldPanel("hero_image_alt"),
        FieldPanel("hero_image_caption"),
        FieldPanel("hero_image_boxed"),
        FieldPanel("hero_image_box_color"),
        FieldPanel("hero_image_box_custom_color"),
        FieldPanel("hero_image_box_border_radius"),
        FieldPanel("author"),
        FieldPanel("published_date"),
        FieldPanel("show_on_homepage"),
        FieldPanel("body"),
    ]

    parent_page_types = [
        "ifi_home_app.CategoryPage"
    ]  # only allow creation under an category
    subpage_types = []  # articles have no children

    @property
    def category(self):
        """The CategoryPage this article lives under."""
        return self.get_parent().specific

    @property
    def style_target(self):
        """The ArticlePage that quick-style edits should actually be saved
        to. Alias pages (e.g. an untranslated locale mirroring another
        locale's page) can't take their own revisions -- Wagtail raises if
        you try (they're an exact, auto-synced copy of their source), so
        edits have to go to the source instead, which Wagtail then
        propagates back to this alias automatically on publish."""
        return self.alias_of.specific if self.alias_of_id else self

    @property
    def toc_entries(self):
        """(level, text) pairs for the table of contents -- see
        _iter_toc_entries() for what counts (top-level headings, multi_column
        column titles)."""
        return list(_iter_toc_entries(self.body))

    @property
    def has_headings(self):
        """True if there's at least one table-of-contents entry, i.e.
        something for it to actually link to."""
        return bool(self.toc_entries)

    def get_context(self, request, *args, **kwargs):
        """Add can_edit_style (whether the visitor can use the on-page style
        panels -- same permission check the save endpoints enforce, see
        article_views.py), block_styles (per-block effective
        alignment/padding/font-size, StreamField value merged with any
        ArticleBlockStyle override -- see _effective_block_styles()), and
        block_style_defaults (see BLOCK_STYLE_DEFAULTS -- powers the "Reset
        to default" button in that same panel)."""
        context = super().get_context(request, *args, **kwargs)
        context["can_edit_style"] = self.style_target.permissions_for_user(request.user).can_edit()
        overrides_by_block_id = {
            style.block_id: style for style in self.style_target.block_styles.all()
        }
        block_styles = _effective_block_styles(self.body, overrides_by_block_id)
        # title/meta/intro aren't part of the body StreamField (they're
        # plain ArticlePage fields, see .article-header in article_page.html)
        # so _effective_block_styles() above never sees them -- box styling
        # for each is added the same way as everything else though, via
        # fixed pseudo ids in the same ArticleBlockStyle override table.
        for pseudo_id in ("article-title", "article-meta", "article-intro"):
            override = overrides_by_block_id.get(pseudo_id)
            block_styles[pseudo_id] = {
                "side_padding": (
                    override.side_padding if override and override.side_padding is not None else 0
                ),
                "box": _effective_box_style(override),
                "text_color": override.text_color if override and override.text_color else "",
                "text_custom_color": (
                    override.text_custom_color if override and override.text_custom_color else ""
                ),
            }
        # the title/meta/intro group as a whole is also independently
        # boxable, same as multi_column's own grid wrapper is on top of
        # each of its columns -- side padding isn't part of this one (see
        # header_side_padding, a plain ArticlePage field driving a CSS
        # custom property in article_page.html instead of this generic
        # mechanism, since the header's own accent underline needs its
        # margin to move together with the indent -- see article_layout.css).
        block_styles["article-header"] = {
            "box": _effective_box_style(overrides_by_block_id.get("article-header")),
        }
        context["block_styles"] = block_styles
        context["block_style_defaults"] = BLOCK_STYLE_DEFAULTS
        return context


class ArticleBlockStyle(models.Model):
    """A per-block style override (alignment/padding/font-size/gap/column
    weights/box) for one styled_text/image/multi_column block -- or one
    multi_column sub-column, keyed by that column's own id (box fields
    only, see _effective_block_styles()) -- inside an ArticlePage's body,
    saved by the on-page block style panel. Deliberately NOT part of the
    StreamField itself -- editing StreamField JSON in place means locating
    a block by id inside potentially-nested content (e.g. a column) and
    going through Wagtail's revision/publish machinery for what's really
    just a styling tweak, which also hit real sharp edges (alias pages
    can't take their own revisions, see ArticlePage.style_target). A plain
    side table keyed by block id sidesteps all of that: no revision, no
    publish, no StreamField parsing, just an upsert. The tradeoff is it's a
    second source of truth -- if a block is deleted and different content
    recreated in its place, that new block gets a new id and simply won't
    match any existing override (harmless: it just renders with its own
    stored defaults, same as never having been styled)."""

    article = models.ForeignKey(
        "ArticlePage", on_delete=models.CASCADE, related_name="block_styles"
    )
    # a real block's own UUID (36 chars) in most cases, but a few synthetic
    # ids built from one (e.g. "<column-uuid>-title" for a multi_column
    # column's own title, see _effective_block_styles()) run longer.
    block_id = models.CharField(max_length=48)

    side_padding = models.FloatField(null=True, blank=True)
    alignment = models.CharField(
        max_length=20, choices=ArticlePage.CONTENT_ALIGNMENT_CHOICES, blank=True
    )
    font_size = models.FloatField(null=True, blank=True)
    width_rem = models.FloatField(null=True, blank=True)
    gap = models.FloatField(null=True, blank=True)
    column_weights = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "multi_column only: one relative weight per column, same order "
            "as the block's own columns. Ignored (falls back to the "
            "block's own per-column weights) if its length no longer "
            "matches the current column count -- e.g. a column was added "
            "or removed in Wagtail after this override was saved."
        ),
    )

    # box styling -- see BLOCK_STYLE_DEFAULTS["box"]/_effective_box_style()
    # in article_models.py. Available on every block type above, and (box
    # fields only) on each multi_column sub-column via its own row keyed by
    # the column's own id.
    box_enabled = models.BooleanField(null=True, blank=True)
    box_border_width = models.FloatField(null=True, blank=True)
    box_border_color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True)
    box_border_custom_color = models.CharField(
        max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR]
    )
    box_border_visible = models.BooleanField(null=True, blank=True)
    box_radius = models.FloatField(null=True, blank=True)
    box_bg_color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True)
    box_bg_custom_color = models.CharField(
        max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR]
    )
    # NOT box_* -- unlike bg/border, text color applies independent of
    # whether the box itself is on (see _effective_heading_style()), so it
    # isn't part of _effective_box_style()'s own dict.
    text_color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True)
    text_custom_color = models.CharField(
        max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR]
    )
    box_padding = models.FloatField(null=True, blank=True)
    box_margin = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "block_id"], name="unique_article_block_style"
            )
        ]


# Model for article category to list articles within category
class CategoryPage(TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """A category of articles, optionally shown only during a specific date range."""

    template = "info_articles/pages/article_category_page.html"

    intro = RichTextField(blank=True)

    COLOR_CHOICES = [
        ("turq", "Turquoise"),
        ("pink", "Pink"),
        ("purple", "Purple"),
    ]

    color = models.CharField(
        max_length=20,
        choices=COLOR_CHOICES,
        default="turq",
        help_text="Accent color used for this category and its articles.",
    )

    # if left blank, category is always shown (a "main" category).
    # if set, category is only shown while today falls within the range.
    active_from = models.DateField(
        null=True,
        blank=True,
        help_text="Leave blank for a category that should always be visible.",
    )
    active_until = models.DateField(null=True, blank=True)

    show_in_menu = models.BooleanField(
        default=False,
        help_text="Show this category in dropdown/sidemenu navigation.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("color"),
        FieldPanel("active_from"),
        FieldPanel("active_until"),
        FieldPanel("show_in_menu"),
    ]

    parent_page_types = ["ifi_home_app.ArticleIndexPage", "ifi_home_app.CategoryPage"]
    subpage_types = [
        "ifi_home_app.ArticlePage",
        "ifi_home_app.CategoryPage",
        "ifi_home_app.StudentUnionCategoryPage",
        "ifi_home_app.ToolPage",
    ]

    @property
    def is_seasonal(self):
        """True for categories only relevant during a specific time period."""
        return bool(self.active_from or self.active_until)

    @property
    def is_currently_active(self):
        """True if a seasonal category's date range covers today."""
        today = timezone.now().date()
        if self.active_from and today < self.active_from:
            return False
        if self.active_until and today > self.active_until:
            return False
        return True

    @property
    def is_visible(self):
        """True if this category should currently be shown to visitors."""
        return not self.is_seasonal or self.is_currently_active

    @property
    def category_section(self):
        """This category's section ('info_articles' or 'news'), inherited from
        the nearest ArticleIndexPage ancestor (categories can nest under other
        categories, so this isn't always the immediate parent)."""
        nearest_index = self.get_ancestors().type(ArticleIndexPage).specific().last()
        return nearest_index.section if nearest_index else None

    def get_context(self, request, *args, **kwargs):
        """Add this category's live subcategories, union categories and articles to the template context."""
        context = super().get_context(request, *args, **kwargs)
        subcategories = (
            CategoryPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
        )
        context["main_subcategories"], context["seasonal_subcategories"] = (
            _split_categories_by_season(subcategories)
        )
        context["union_categories"] = (
            StudentUnionCategoryPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
        )
        context["articles"] = (
            ArticlePage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("-published_date")
        )
        context["tools"] = (
            ToolPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("title")
        )
        return context


# parent page to list articles categories
class ArticleIndexPage(TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """Landing page listing all article categories and suggested articles."""

    template = "info_articles/pages/article_index_page.html"  # custom path

    intro = RichTextField(blank=True)

    SECTION_CHOICES = [
        ("info_articles", "Info articles"),
        ("news", "News"),
        ("hub", "Hub (structural only, not a content section itself)"),
    ]

    section = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES,
        default="info_articles",
        help_text=(
            "Which part of the site this index (and the categories under it) "
            "belongs to - used to keep e.g. news categories out of the info-articles "
            "sidemenu, and vice versa. Use 'Hub' for a purely structural index "
            "whose children are other index pages (e.g. the top-level page holding "
            "both the info-articles and news indexes)."
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("section"),
    ]

    subpage_types = [
        "ifi_home_app.ArticleIndexPage",
        "ifi_home_app.CategoryPage",
        "ifi_home_app.StudentUnionCategoryPage",
        "ifi_home_app.ToolPage",
    ]

    # overriding for extra data

    def get_context(self, request, *args, **kwargs):
        """Add main/seasonal categories, union categories and suggested articles to the template context."""
        context = super().get_context(request, *args, **kwargs)
        categories = (
            CategoryPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
        )
        context["main_categories"], context["seasonal_categories"] = (
            _split_categories_by_season(categories)
        )
        context["union_categories"] = (
            StudentUnionCategoryPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
        )
        context["suggested_articles"] = (
            ArticlePage.objects.descendant_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("-published_date")[:4]
        )
        context["tools"] = (
            ToolPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("title")
        )
        return context


# Model for a student union's own page, published under a StudentUnionCategoryPage
class UnionPage(TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """A single student union's page: contact info, purpose, activities and members."""

    template = "info_articles/pages/union_page.html"

    email = models.EmailField(blank=True)
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    purpose = RichTextField(blank=True, help_text="What the union is about.")
    activities = RichTextField(blank=True, help_text="Activities the union offers.")

    TYPE_CHOICES = [
        ("general", "Open to everyone"),
        ("program", "Program-specific"),
    ]

    union_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="general",
        help_text="Whether this union is open to everyone or tied to a specific program.",
    )

    website_url = models.URLField(blank=True)

    SOCIAL_PLATFORM_CHOICES = [
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("discord", "Discord"),
        ("linkedin", "LinkedIn"),
        ("tiktok", "TikTok"),
        ("other", "Other"),
    ]

    social_links = StreamField(
        [
            (
                "social_link",
                blocks.StructBlock(
                    [
                        (
                            "platform",
                            blocks.ChoiceBlock(choices=SOCIAL_PLATFORM_CHOICES),
                        ),
                        ("url", blocks.URLBlock()),
                    ]
                ),
            ),
        ],
        use_json_field=True,
        blank=True,
    )

    member_count_sitting = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of sitting board members. Leave blank to hide.",
    )
    member_count_intern = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of interns. Leave blank to hide.",
    )

    sitting_members = StreamField(
        [
            (
                "member",
                blocks.StructBlock(
                    [
                        ("name", blocks.CharBlock()),
                        (
                            "role",
                            blocks.CharBlock(
                                help_text="Role within the union, e.g. Chair, Treasurer."
                            ),
                        ),
                        (
                            "school_email",
                            blocks.EmailBlock(required=False),
                        ),
                        ("picture", ImageChooserBlock(required=False)),
                    ]
                ),
            ),
        ],
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("email"),
        FieldPanel("logo"),
        FieldPanel("union_type"),
        FieldPanel("purpose"),
        FieldPanel("activities"),
        FieldPanel("website_url"),
        FieldPanel("social_links"),
        FieldPanel("member_count_sitting"),
        FieldPanel("member_count_intern"),
        FieldPanel("sitting_members"),
    ]

    parent_page_types = ["ifi_home_app.StudentUnionCategoryPage"]
    subpage_types = []  # union pages have no children

    @property
    def union_category(self):
        """The StudentUnionCategoryPage this union lives under."""
        return self.get_parent().specific


# Model for the category listing all student unions
class StudentUnionCategoryPage(TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """A category page whose only children are student union pages."""

    template = "info_articles/pages/studentunion_category_page.html"

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    parent_page_types = ["ifi_home_app.ArticleIndexPage", "ifi_home_app.CategoryPage"]
    subpage_types = ["ifi_home_app.UnionPage"]

    def get_context(self, request, *args, **kwargs):
        """Add this category's live student unions to the template context."""
        context = super().get_context(request, *args, **kwargs)
        context["unions"] = (
            UnionPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("title")
        )
        return context


# Model for an ifi-tool's own page (e.g. event calendar, map webpage)
class ToolPage(TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """A single ifi-tool's page: what it is, an image, an optional link and maker."""

    template = "info_articles/pages/tool_page.html"

    description = RichTextField(help_text="What this tool is / what it does.")
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    image_overlay = models.BooleanField(
        default=True,
        help_text=(
            "Darken the image so the title/maker stay readable when overlaid on it. "
            "Turn off to show the image plain, with the title below it instead."
        ),
    )
    link = models.URLField(
        blank=True,
        help_text="Link to the tool itself, e.g. the calendar or map webpage.",
    )
    made_by = models.CharField(
        max_length=250,
        blank=True,
        help_text="Who made this tool, if relevant.",
    )
    preview_images = StreamField(
        [
            ("image", ImageChooserBlock()),
        ],
        use_json_field=True,
        blank=True,
        max_num=3,
        help_text="Up to three screenshots/previews of the tool, shown below the description.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        FieldPanel("image"),
        FieldPanel("image_overlay"),
        FieldPanel("link"),
        FieldPanel("made_by"),
        FieldPanel("preview_images"),
    ]

    parent_page_types = ["ifi_home_app.ArticleIndexPage", "ifi_home_app.CategoryPage"]
    subpage_types = []  # tool pages have no children
