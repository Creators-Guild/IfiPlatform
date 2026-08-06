"""Template tags for linking to the article index/category pages, e.g. from the sidemenu."""

from django import template
from ifi_home_app.models.article_models import get_section_categories, get_section_index

register = template.Library()


@register.simple_tag
def get_article_index():
    """Return the site's info-articles ArticleIndexPage, used to build links to it."""
    return get_section_index("info_articles")


@register.simple_tag
def get_categories():
    """Return currently visible info-article categories flagged for menu display, for the sidemenu."""
    return get_section_categories("info_articles")


@register.simple_tag
def get_news_index():
    """Return the site's news ArticleIndexPage, used to build links to it."""
    return get_section_index("news")


@register.simple_tag
def get_news_categories():
    """Return currently visible news categories flagged for menu display, for the sidemenu."""
    return get_section_categories("news")
