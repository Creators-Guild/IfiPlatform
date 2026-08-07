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
    """A single image with layout/caption/box options, shared by the top-level
    'image' block and the image option inside multi-column text."""
    return blocks.StructBlock(
        [
            ("image", ImageChooserBlock()),
            (
                "alignment",
                blocks.ChoiceBlock(
                    choices=[
                        ("left", "Left"),
                        ("center", "Center"),
                        ("right", "Right"),
                    ],
                    default="center",
                ),
            ),
            (
                "width_rem",
                blocks.FloatBlock(
                    default=20,
                    help_text="Width, in rem.",
                ),
            ),
            (
                "alt_text",
                blocks.CharBlock(
                    required=False,
                    help_text="Accessible description. Leave blank to use the image's own title.",
                ),
            ),
            ("caption", blocks.CharBlock(required=False)),
            (
                "boxed",
                blocks.BooleanBlock(
                    required=False,
                    default=False,
                    help_text="Draw a border/box around the image, title and description.",
                ),
            ),
            (
                "box_color",
                blocks.ChoiceBlock(
                    choices=COLOR_CHOICES,
                    default="bg-light",
                    required=False,
                    help_text="Box background color (only applies when 'boxed' is enabled).",
                ),
            ),
            (
                "box_custom_color",
                blocks.CharBlock(
                    required=False,
                    validators=[HEX_COLOR_VALIDATOR],
                    help_text="Hex code, e.g. #ff8800. Only used when color is set to 'Custom'.",
                ),
            ),
            (
                "box_border_radius",
                blocks.FloatBlock(
                    min_value=0,
                    max_value=5,
                    default=0.75,
                    help_text="Box corner rounding, in rem (0 = square corners). Only applies when 'boxed' is enabled.",
                ),
            ),
            (
                "side_padding",
                blocks.FloatBlock(
                    default=0,
                    help_text="Left/right padding, in rem (0 = none).",
                ),
            ),
        ],
        icon="image",
    )


def article_styled_text_block():
    """A rich text block with layout options (alignment, letter size, side
    padding). Kept as its own block type rather than added to the existing
    plain 'paragraph' block -- that one's value is just a bare RichText
    string, and changing its shape to a struct would need a data migration
    to convert every existing paragraph across every article. This way
    existing content is untouched; editors opt into the new block going
    forward."""
    return blocks.StructBlock(
        [
            ("text", blocks.RichTextBlock()),
            (
                "alignment",
                blocks.ChoiceBlock(
                    choices=[
                        ("left", "Left"),
                        ("center", "Center"),
                        ("right", "Right"),
                    ],
                    default="left",
                ),
            ),
            (
                "font_size",
                blocks.FloatBlock(
                    default=1,
                    help_text="Font size, in rem.",
                ),
            ),
            (
                "side_padding",
                blocks.FloatBlock(
                    default=1,
                    help_text="Left/right padding, in rem (0 = none).",
                ),
            ),
        ],
        icon="pilcrow",
        label="Styled Text",
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
                    (
                        "alignment",
                        blocks.ChoiceBlock(
                            choices=[
                                ("left", "Left"),
                                ("center", "Center"),
                                ("right", "Right"),
                            ],
                            default="left",
                        ),
                    ),
                    (
                        "font_size",
                        blocks.FloatBlock(
                            default=1.5,
                            help_text="Font size, in rem.",
                        ),
                    ),
                    (
                        "side_padding",
                        blocks.FloatBlock(
                            default=0,
                            help_text="Left/right padding, in rem (0 = none).",
                        ),
                    ),
                ]
            ),
        ),
        ("paragraph", blocks.RichTextBlock(icon="pilcrow")),
        ("styled_text", article_styled_text_block()),
        (
            "multi_column",
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
                                            ],
                                            required=False,
                                        ),
                                    ),
                                    (
                                        "width",
                                        blocks.IntegerBlock(
                                            min_value=1,
                                            max_value=10,
                                            default=1,
                                            label="Column weight",
                                            help_text=(
                                                "How much space this column takes relative "
                                                "to the other columns -- not a literal width, "
                                                "just a ratio between them (e.g. weight 2 next "
                                                "to weight 1 makes this column twice as wide)."
                                            ),
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
                    (
                        "gap",
                        blocks.FloatBlock(
                            min_value=0,
                            max_value=10,
                            default=2,
                            help_text="Space between columns, in rem.",
                        ),
                    ),
                    (
                        "side_padding",
                        blocks.FloatBlock(
                            default=1,
                            help_text="Left/right padding around the whole multi-column block, in rem (0 = none).",
                        ),
                    ),
                ],
                icon="placeholder",
                label="Multi-column Text",
            ),
        ),
        ("image", article_image_block()),
    ]


def article_box_block():
    """A container with its own background color, border color and corner
    radius, holding any of the other body block types (but not another
    box, to avoid unbounded nesting -- see _body_content_blocks())."""
    return blocks.StructBlock(
        [
            (
                "background_color",
                blocks.ChoiceBlock(choices=COLOR_CHOICES, default="bg-light"),
            ),
            (
                "background_custom_color",
                blocks.CharBlock(
                    required=False,
                    validators=[HEX_COLOR_VALIDATOR],
                    help_text="Hex code, e.g. #ff8800. Only used when background color is set to 'Custom'.",
                ),
            ),
            (
                "border_color",
                blocks.ChoiceBlock(choices=COLOR_CHOICES, default="black"),
            ),
            (
                "border_custom_color",
                blocks.CharBlock(
                    required=False,
                    validators=[HEX_COLOR_VALIDATOR],
                    help_text="Hex code, e.g. #ff8800. Only used when border color is set to 'Custom'.",
                ),
            ),
            (
                "border_radius",
                blocks.FloatBlock(
                    min_value=0,
                    max_value=5,
                    default=0.75,
                    help_text="Corner rounding, in rem (0 = square corners).",
                ),
            ),
            (
                "float",
                blocks.ChoiceBlock(
                    choices=[
                        ("none", "None (full width)"),
                        ("left", "Left"),
                        ("right", "Right"),
                    ],
                    default="none",
                    help_text=(
                        "Floating the box (like the hero image) lets the article's "
                        "surrounding paragraphs wrap around it and reclaim the full "
                        "width again once they've scrolled past it -- no separate "
                        "'columns' needed for that, ordinary paragraphs do it "
                        "automatically. 'None' makes it a full-width block instead."
                    ),
                ),
            ),
            (
                "float_width",
                blocks.FloatBlock(
                    min_value=10,
                    max_value=100,
                    default=40,
                    help_text="Width as a % of the article's content width. Only applies when floated.",
                ),
            ),
            (
                "content",
                blocks.StreamBlock(_body_content_blocks(), required=False),
            ),
        ],
        icon="placeholder",
        label="Box",
    )


def _iter_toc_entries(body_stream):
    """Recursively walks a body StreamValue (or a box's own nested content
    StreamValue, which holds the same block types) yielding (level, text)
    pairs for anything the table of contents should link to: top-level
    headings, headings nested inside a box, and multi_column column titles
    (treated as h3s, since they're a smaller heading-like label rather than
    a real 'heading' block -- see article_body_blocks.html, which gives
    both an id built the same way (slugify(text)), so these pairs line up
    with the actual anchors on the page. Box content can't itself contain
    another box (see _body_content_blocks()), so this can't recurse
    forever."""
    for block in body_stream:
        if block.block_type == "heading":
            yield block.value["level"], block.value["text"]
        elif block.block_type == "multi_column":
            for column in block.value["columns"]:
                if column.get("title"):
                    yield "h3", column["title"]
        elif block.block_type == "box":
            yield from _iter_toc_entries(block.value["content"])


def _effective_block_styles(body_stream, overrides_by_block_id):
    """Recursively walks a body StreamValue (or a box's/column's own nested
    content, same block types) yielding {block_id: {...}} for every
    heading/styled_text/image/multi_column block, each block's own
    StreamField value merged with any ArticleBlockStyle override for it
    (override wins where set, otherwise the block's own stored value). Kept
    as plain dicts rather than touching block.value.font_size etc. directly
    in templates, so the "was this overridden by the on-page panel" logic
    lives in one place. Same recursion shape as _iter_toc_entries -- box
    content can't itself contain another box, so this can't recurse
    forever."""
    styles = {}
    for block in body_stream:
        block_id = str(block.id)
        override = overrides_by_block_id.get(block_id)
        if block.block_type == "heading":
            styles[block_id] = {
                "font_size": (
                    override.font_size
                    if override and override.font_size is not None
                    else block.value["font_size"]
                ),
                "side_padding": (
                    override.side_padding
                    if override and override.side_padding is not None
                    else block.value["side_padding"]
                ),
                "alignment": (
                    override.alignment
                    if override and override.alignment
                    else block.value["alignment"]
                ),
            }
        elif block.block_type == "styled_text":
            styles[block_id] = {
                "font_size": (
                    override.font_size
                    if override and override.font_size is not None
                    else block.value["font_size"]
                ),
                "side_padding": (
                    override.side_padding
                    if override and override.side_padding is not None
                    else block.value["side_padding"]
                ),
                "alignment": (
                    override.alignment
                    if override and override.alignment
                    else block.value["alignment"]
                ),
            }
        elif block.block_type == "image":
            styles[block_id] = {
                "alignment": (
                    override.alignment
                    if override and override.alignment
                    else block.value["alignment"]
                ),
                "width_rem": (
                    override.width_rem
                    if override and override.width_rem is not None
                    else block.value["width_rem"]
                ),
                "side_padding": (
                    override.side_padding
                    if override and override.side_padding is not None
                    else block.value["side_padding"]
                ),
            }
        elif block.block_type == "multi_column":
            own_weights = [column["width"] for column in block.value["columns"]]
            override_weights = override.column_weights if override else None
            styles[block_id] = {
                "side_padding": (
                    override.side_padding
                    if override and override.side_padding is not None
                    else block.value["side_padding"]
                ),
                "gap": (
                    override.gap
                    if override and override.gap is not None
                    else block.value["gap"]
                ),
                "column_weights": (
                    override_weights
                    if override_weights and len(override_weights) == len(own_weights)
                    else own_weights
                ),
            }
            for column in block.value["columns"]:
                styles.update(_effective_block_styles(column["content"], overrides_by_block_id))
        elif block.block_type == "box":
            styles.update(_effective_block_styles(block.value["content"], overrides_by_block_id))
    return styles


# Default values for each on-page-editable field, per block type -- powers
# the "Reset to default" button in the on-page block style panel
# (article_block_style.js, via ArticlePage.get_context()). Kept in sync by
# hand with each field's own default= elsewhere in this file
# (article_styled_text_block(), article_image_block(), the multi_column
# StructBlock's own fields, and ArticlePage's title_font_size/hero_image_*
# etc.) -- there's no single shared source, since some of these are
# StreamField block defaults and some are plain Django model field
# defaults, two different mechanisms.
BLOCK_STYLE_DEFAULTS = {
    "heading": {"alignment": "left", "font_size": 1.5, "side_padding": 0},
    "styled_text": {"side_padding": 1, "alignment": "left", "font_size": 1},
    "image": {"alignment": "center", "width_rem": 20, "side_padding": 0},
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
}


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
    show_in_newsbar = models.BooleanField(
        default=True,
        help_text="Whether this article can be suggested in the homepage newsbar (only relevant for news articles).",
    )
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

    # allows for mutiple sections of one of these types:
    body = StreamField(
        _body_content_blocks() + [("box", article_box_block())],
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("hero_image_position"),
        FieldPanel("hero_image_width_rem"),
        FieldPanel("hero_image_side_padding"),
        FieldPanel("hero_image_title"),
        FieldPanel("hero_image_alt"),
        FieldPanel("hero_image_caption"),
        FieldPanel("hero_image_boxed"),
        FieldPanel("hero_image_box_color"),
        FieldPanel("hero_image_box_custom_color"),
        FieldPanel("hero_image_box_border_radius"),
        FieldPanel("author"),
        FieldPanel("published_date"),
        FieldPanel("show_in_newsbar"),
        FieldPanel("show_on_homepage"),
        FieldPanel("content_side_padding"),
        FieldPanel("content_alignment"),
        FieldPanel("content_font_size"),
        FieldPanel("title_alignment"),
        FieldPanel("title_font_size"),
        FieldPanel("intro_alignment"),
        FieldPanel("intro_font_size"),
        FieldPanel("meta_alignment"),
        FieldPanel("meta_font_size"),
        FieldPanel("header_side_padding"),
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
        _iter_toc_entries() for what counts (top-level headings, headings
        nested in a box, multi_column column titles)."""
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
        context["block_styles"] = _effective_block_styles(self.body, overrides_by_block_id)
        context["block_style_defaults"] = BLOCK_STYLE_DEFAULTS
        return context


class ArticleBlockStyle(models.Model):
    """A per-block style override (alignment/padding/font-size/gap/column
    weights) for one styled_text/image/multi_column block inside an
    ArticlePage's body,
    saved by the on-page block style panel. Deliberately NOT part of the
    StreamField itself -- editing StreamField JSON in place means locating
    a block by id inside potentially-nested content (a column, a box) and
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
    block_id = models.CharField(max_length=36)

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
