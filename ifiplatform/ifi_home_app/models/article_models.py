"""Models for Wagtail-managed information articles: categories, index and article pages."""

from django.core.validators import RegexValidator
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
                "size",
                blocks.ChoiceBlock(
                    choices=[
                        ("small", "Small"),
                        ("medium", "Medium"),
                        ("large", "Large"),
                    ],
                    default="medium",
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
                    choices=[
                        ("bg-light", "Light"),
                        ("turq", "Turquoise"),
                        ("pink", "Pink"),
                        ("purple", "Purple"),
                        ("black", "Black"),
                        ("custom", "Custom (hex code)"),
                    ],
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
        ],
        icon="image",
    )


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

    intro = models.CharField(max_length=250, blank=True)
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

    HERO_SIZE_CHOICES = [
        ("small", "Small"),
        ("medium", "Medium"),
        ("large", "Large"),
        ("full", "Full width"),
    ]

    hero_image_size = models.CharField(
        max_length=20,
        choices=HERO_SIZE_CHOICES,
        default="medium",
    )

    hero_image_alt = models.CharField(
        max_length=250,
        blank=True,
        help_text="Accessible description of the image. Leave blank to use the image's own title.",
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
    # metadata
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    published_date = models.DateField(null=True, blank=True)
    show_on_homepage = models.BooleanField(
        default=True,
        help_text="Whether this article can be suggested on the homepage (newsbar/articles bar).",
    )

    # allows for mutiple sections of one of these types:
    body = StreamField(
        [
            # allows for indented headings
            (
                "heading",
                blocks.StructBlock(
                    [
                        ("text", blocks.CharBlock()),
                        (
                            "level",
                            blocks.ChoiceBlock(
                                choices=[("h2", "H2"), ("h3", "H3")], default="h2"
                            ),
                        ),
                    ]
                ),
            ),
            ("paragraph", blocks.RichTextBlock(icon="pilcrow")),
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
                                                help_text=(
                                                    "Relative width vs. the "
                                                    "other columns (e.g. 2 is "
                                                    "twice as wide as 1)."
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
                    ],
                    icon="placeholder",
                    label="Multi-column Text",
                ),
            ),
            ("image", article_image_block()),
        ],
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("hero_image_position"),
        FieldPanel("hero_image_size"),
        FieldPanel("hero_image_alt"),
        FieldPanel("hero_image_caption"),
        FieldPanel("hero_image_boxed"),
        FieldPanel("hero_image_box_color"),
        FieldPanel("hero_image_box_custom_color"),
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
