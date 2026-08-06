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


@register.filter
def grouped_columns(columns):
    """Groups a multi_column block's flat column list into outer flex
    'cells' for article_body_blocks.html.

    A column with wrap=False starts a new cell and becomes that cell's
    'main' content. Any column(s) immediately after it with wrap=True are
    absorbed into that SAME cell as internal floats (on whichever side
    their 'wrap_side' says), rather than becoming their own outer flex
    cell -- this is what lets an image sit inside the same lane as the
    column whose text should wrap around it (main flows, reclaiming space
    once past the float), while a later wrap=False column starts a
    completely separate outer lane, unaffected by anything happening in
    the previous one.

    Returns a list of {'main': <column or None>, 'floats': [<column>, ...]}
    dicts, one per outer cell, in column order. 'main' is None only for the
    edge case of a wrap=True column appearing before any wrap=False column
    -- it still gets its own cell, just with no flowing text of its own.
    """
    cells = []
    current = None
    for column in columns:
        if not column.get("wrap"):
            current = {"main": column, "floats": []}
            cells.append(current)
        elif current is not None:
            current["floats"].append(column)
        else:
            current = {"main": None, "floats": [column]}
            cells.append(current)
    return cells
