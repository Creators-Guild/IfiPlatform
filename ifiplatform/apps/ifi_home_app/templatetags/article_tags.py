"""Template tags for linking to the article index/category pages, e.g. from the sidemenu."""

from django import template
from django.utils import timezone
from wagtail.models import Locale

from ifi_home_app.models.article_models import get_section_categories, get_section_index
from ifi_home_app.models.event_models import EventIndexPage, PeoplySyncState, SITE_TIMEZONE

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


@register.simple_tag
def get_event_index():
    """Return the site's EventIndexPage, used to build links to it (e.g. the
    sidemenu's "Events" entry)."""
    return EventIndexPage.objects.live().filter(locale=Locale.get_active()).first()


@register.simple_tag
def get_peoply_last_synced():
    """When sync_peoply_events last ran successfully, converted to
    SITE_TIMEZONE -- None if it's never run. Stored (and would otherwise
    render) in UTC, this project's settings.TIME_ZONE, not Oslo -- without
    the conversion this is off by the UTC offset (2h in summer/CEST, 1h in
    winter/CET). Site-wide, not per-event: shown on Peoply-sourced event
    pages so visitors know how fresh the data is, even though the event's
    own page itself may have been created long ago (sync is create-only)."""
    synced_at = PeoplySyncState.last_synced_at()
    return timezone.localtime(synced_at, timezone=SITE_TIMEZONE) if synced_at else None
