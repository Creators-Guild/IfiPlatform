"""UnionPage and StudentUnionCategoryPage -- mutually coupled with each
other (a category whose only children are unions), but not with the
Article/Category cluster in pages.py beyond one-directional queries.

Design rationale/history: docs/claude_context/article_unions.md"""

from django.db import models
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Locale, Page

from .blocks import union_group_block
from ..page_mixins import BannerStyleMixin, EditorModeMixin, TranslationWarningMixin


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
    vedtekter = RichTextField(
        blank=True,
        help_text="Optional -- the union's bylaws/statutes, shown on its own page.",
    )
    vedtekter_url = models.URLField(
        blank=True,
        help_text="Optional -- link to the full bylaws/statutes elsewhere (e.g. a PDF or the union's own site), shown alongside the text above.",
    )

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

    STATUS_CHOICES = [
        ("active", "Active"),
        ("retired", "Retired -- no longer active"),
        ("unknown", "Unknown -- can't confirm if still active"),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Active unions are shown in the main listing, retired ones under 'Old, but not forgotten', and unknown ones (e.g. no working contact/website found) under 'Missing in action'.",
    )
    show_in_menu = models.BooleanField(
        default=False,
        help_text="Show this union in the homepage navigation menu's Student Unions dropdown.",
    )

    website_url = models.URLField(blank=True)
    signup_url = models.URLField(
        blank=True,
        help_text="Optional -- link to a membership/interest sign-up form (e.g. a Google Form to join or register interest).",
    )
    peoply_organization_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Optional -- this union's organization ID on Peoply (from its Peoply page URL). Setting this enables automatic event sync via sync_peoply_events.",
    )

    SOCIAL_PLATFORM_CHOICES = [
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("discord", "Discord"),
        ("linkedin", "LinkedIn"),
        ("tiktok", "TikTok"),
        ("github", "GitHub"),
        ("slack", "Slack"),
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
        FieldPanel("status"),
        FieldPanel("show_in_menu"),
        FieldPanel("purpose"),
        FieldPanel("activities"),
        FieldPanel("vedtekter"),
        FieldPanel("vedtekter_url"),
        FieldPanel("website_url"),
        FieldPanel("signup_url"),
        FieldPanel("peoply_organization_id"),
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

    def get_context(self, request, *args, **kwargs):
        """Add upcoming_events: live, still-upcoming EventPages tagging
        this union. Imported locally to avoid a circular import -- see
        docs/claude_context/article_unions.md."""
        context = super().get_context(request, *args, **kwargs)
        from ifi_home_app.models.event_models import upcoming_events_for_union

        context["upcoming_events"] = upcoming_events_for_union(self)
        return context


# Model for the category listing all student unions
class StudentUnionCategoryPage(EditorModeMixin, BannerStyleMixin, TranslationWarningMixin, Page):  # pylint: disable=too-many-ancestors
    """A category page whose only children are student union pages."""

    template = "info_articles/pages/studentunion_category_page.html"

    intro = RichTextField(blank=True)
    general_info = RichTextField(
        blank=True,
        help_text="Optional -- a short paragraph of general information about student unions, shown below the intro.",
    )

    # Editor-curated groupings shown above the automatic "All unions"
    # listing -- see docs/claude_context/article_unions.md.
    union_groups = StreamField(
        [
            ("group", union_group_block()),
            (
                "row",
                blocks.StructBlock(
                    [
                        (
                            "title",
                            blocks.CharBlock(
                                required=False,
                                help_text="Optional -- a heading shown above the whole row, e.g. 'Foreninger'.",
                            ),
                        ),
                        (
                            "groups",
                            blocks.ListBlock(
                                union_group_block(),
                                help_text="Union groups to place side by side in this row.",
                            ),
                        ),
                    ],
                    icon="grip",
                    label="Row of union groups",
                ),
            ),
        ],
        use_json_field=True,
        blank=True,
        help_text=(
            "Optional -- organize unions into titled groups, standalone or "
            "side by side in a row. Every union also always appears in "
            "the 'All unions' listing below, regardless of grouping."
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("general_info"),
        FieldPanel("union_groups"),
    ]

    parent_page_types = ["ifi_home_app.ArticleIndexPage", "ifi_home_app.CategoryPage"]
    subpage_types = ["ifi_home_app.UnionPage"]

    def get_context(self, request, *args, **kwargs):
        """Split live unions into active/retired/unknown, plus automatic
        program_unions/other_unions groupings. See
        docs/claude_context/article_unions.md."""
        context = super().get_context(request, *args, **kwargs)
        context["can_edit_style"] = self.can_edit_in_editor_mode(request.user)
        context["can_sync_mirrored_page"] = self.can_sync_mirrored_page(request.user)
        unions = (
            UnionPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("title")
        )
        active_unions = unions.filter(status="active")
        context["active_unions"] = active_unions
        context["retired_unions"] = unions.filter(status="retired")
        context["unknown_unions"] = unions.filter(status="unknown")

        curated_ids = set()
        for block in self.union_groups:
            if block.block_type == "row":
                for group in block.value["groups"]:
                    curated_ids.update(
                        item["union"].id for item in group["unions"] if item["union"]
                    )
            elif block.block_type == "group":
                curated_ids.update(
                    item["union"].id for item in block.value["unions"] if item["union"]
                )

        context["program_unions"] = active_unions.filter(union_type="program")
        context["other_unions"] = (
            active_unions.exclude(id__in=curated_ids).exclude(union_type="program")
        )
        return context
