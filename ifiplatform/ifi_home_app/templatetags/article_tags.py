"""Template tags for linking to the article index/category pages, e.g. from the sidemenu."""

from django import template
from ifi_home_app.models.article_models import ArticleIndexPage, CategoryPage

register = template.Library()


@register.simple_tag
def get_article_index():
    """Return the site's single ArticleIndexPage, used to build links to it."""
    return ArticleIndexPage.objects.live().first()


@register.simple_tag
def get_categories():
    """Return all currently visible article categories, for the sidemenu."""
    return [c for c in CategoryPage.objects.live() if c.is_visible]
