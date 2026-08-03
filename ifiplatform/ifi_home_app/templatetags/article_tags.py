"""Template tags for linking to the article index/category pages, e.g. from the sidemenu."""

from django import template
from wagtail.models import Locale
from ifi_home_app.models.article_models import ArticleIndexPage, CategoryPage

register = template.Library()


@register.simple_tag
def get_article_index():
    """Return the site's single ArticleIndexPage, used to build links to it."""
    return ArticleIndexPage.objects.live().filter(locale=Locale.get_active()).first()


@register.simple_tag
def get_categories():
    """Return all currently visible article categories, for the sidemenu."""
    categories = CategoryPage.objects.live().filter(locale=Locale.get_active())
    return [c for c in categories if c.is_visible]
