from django.db import models
from django.conf import settings
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.images.blocks import ImageChooserBlock
from wagtail import blocks

# !Wagtail has no views and don't need any!

# Current tree: ArticleIndexPage -> ArticleCategory -> ArticlePage

# Model for Articles
class ArticlePage(Page):
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
    # metadata
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    published_date = models.DateField(null=True, blank=True)

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
                "two_column",
                blocks.StructBlock(
                    [
                        ("left", blocks.RichTextBlock()),
                        ("right", blocks.RichTextBlock()),
                    ],
                    icon="placeholder",
                    label="Two Column Text",
                ),
            ),
            ("image", ImageChooserBlock(icon="image")),
        ],
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("author"),
        FieldPanel("published_date"),
        FieldPanel("body"),
    ]

    parent_page_types = [
        "ifi_home_app.CategoryPage"
    ]  # only allow creation under an category
    subpage_types = []  # articles have no children


# Model for article category to list articles within category
class CategoryPage(Page):
    template = "info_articles/pages/article_category_page.html"

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    parent_page_types = ["ifi_home_app.ArticleIndexPage"]
    subpage_types = ["ifi_home_app.ArticlePage"]

    def get_context(self, request):
        context = super().get_context(request)
        context["articles"] = (
            ArticlePage.objects.child_of(self).live().order_by("-published_date")
        )
        return context


# parent page to list articles categories
class ArticleIndexPage(Page):
    template = "info_articles/pages/article_index_page.html"  # custom path

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["ifi_home_app.CategoryPage"]

    # overriding for extra data

    def get_context(self, request):
        context = super().get_context(request)
        context["categories"] = CategoryPage.objects.child_of(self).live()
        return context