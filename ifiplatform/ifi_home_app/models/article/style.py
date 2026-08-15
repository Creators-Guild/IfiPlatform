"""Whole-article styling model -- see ArticleStyle's own docstring."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (
    BOX_COLOR_CHOICES,
    COLOR_CHOICES,
    CONTENT_ALIGNMENT_CHOICES,
    HERO_POSITION_CHOICES,
    HEX_COLOR_VALIDATOR,
    TITLE_ALIGNMENT_CHOICES,
)


class ArticleStyle(models.Model):
    """Whole-article styling, edited on-page via editor mode
    (article_quick_style.js) and deliberately outside Wagtail's
    revision/publish system -- styling shouldn't differ between locale
    translations of "the same" article. Keyed by translation_key, shared
    across every locale copy of one article. See ArticlePage.style.

    Design rationale/history: docs/claude_context/article_style_and_page_mixins.md"""

    translation_key = models.UUIDField(unique=True)

    # hero_image itself and its title/alt/caption stay on ArticlePage --
    # those are content, not styling.
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
    hero_image_boxed = models.BooleanField(
        default=False,
        help_text="Draw a border/box around the image, title and description.",
    )
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
    # editable version of .image-figure--boxed's own fixed shadow in
    # article_image.css.
    hero_image_box_shadow_enabled = models.BooleanField(
        default=True,
        help_text="Draw a shadow under the box. Only applies when 'boxed' is enabled.",
    )
    hero_image_box_shadow_strength = models.FloatField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        help_text=(
            "Shadow intensity multiplier (1 = the box's original fixed shadow size, 0 = none). "
            "Only applies when 'boxed' and shadow are enabled."
        ),
    )
    hero_image_box_shadow_color = models.CharField(
        max_length=20,
        choices=BOX_COLOR_CHOICES,
        blank=True,
        help_text="Shadow color -- blank keeps the page's own theme shadow color.",
    )
    hero_image_box_shadow_custom_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[HEX_COLOR_VALIDATOR],
        help_text="Hex code, e.g. #ff8800. Only used when shadow color is set to 'Custom'.",
    )

    content_side_padding = models.FloatField(
        default=0,
        help_text=(
            "Left/right padding around the whole article body, in rem (0 = "
            "none). Applies on top of the site's own layout padding, and "
            "stacks with any per-block side padding inside it."
        ),
    )
    content_alignment = models.CharField(
        max_length=20,
        choices=CONTENT_ALIGNMENT_CHOICES,
        default="left",
        help_text=(
            "Saving a change to this OVERWRITES the alignment of every "
            "alignment-capable block in the article body (heading, "
            "paragraph, image, image captions, column titles) -- see "
            "save_quick_style's apply_alignment_to_blocks handling and "
            "alignment_capable_block_ids(). A block can opt out via its own "
            "'exclude_from_global_alignment' flag on ArticleBlockStyle. "
            "Does not affect the title/intro/meta block above the body, "
            "which has its own separate alignment controls."
        ),
    )
    content_font_size_multiplier = models.FloatField(
        default=1,
        help_text=(
            "Multiplies the effective font size of every heading/paragraph/"
            "image-caption/column-title block in the body, on top of each "
            "block's own font size (1 = no change) -- see "
            "_effective_heading_style()'s display_font_size. Unlike "
            "alignment above, this never overwrites any block's own stored "
            "font_size -- it's a display-time scale, not a per-block "
            "override. Title, intro and meta have their own separate font "
            "size controls, unaffected by this."
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

    toc_icon_size = models.FloatField(
        default=1.3,
        help_text=(
            "Size of the table-of-contents icon (the circular \"contents\" "
            "button next to the title), in rem. The button's own circle "
            "grows and shrinks along with it."
        ),
    )

    # 2/8 reproduce hero_image's original fixed shadow exactly at strength=1
    # -- see docs/claude_context/article_style_and_page_mixins.md.
    @property
    def hero_image_box_shadow_offset(self):
        return 2 * self.hero_image_box_shadow_strength

    @property
    def hero_image_box_shadow_blur(self):
        return 8 * self.hero_image_box_shadow_strength
