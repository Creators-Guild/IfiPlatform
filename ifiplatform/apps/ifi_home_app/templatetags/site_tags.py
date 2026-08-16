"""Template tags for small site-wide content, e.g. the rotating header message."""

import random

from django import template
from wagtail.models import Locale

from ..models.site_models import HeaderMessage

register = template.Library()


@register.simple_tag
def get_header_message():
    """Return a random active header message -- a fresh pick on every page
    load, since this is called from top_header.html on every render."""
    messages = list(
        HeaderMessage.objects.filter(
            is_active=True, locale=Locale.get_active()
        )
    )
    if not messages:
        return None
    return random.choice(messages)


@register.simple_tag(takes_context=True)
def translated_page_url(context, locale_code):
    """URL of the current Wagtail page's translation into the given locale.

    Wagtail lets each locale have its own slug, so Django's generic language
    switcher (which just swaps the URL's language prefix) produces a broken
    URL whenever the slugs differ between locales. This walks up from the
    current page to the nearest ancestor that does have a translation into
    `locale_code`, and returns its real URL instead. Falls back to the
    current path for non-Wagtail views (e.g. the home page).
    """
    request = context.get("request")
    fallback = request.path if request else "/"

    page = context.get("page")
    if not page:
        return fallback

    try:
        locale = Locale.objects.get(language_code=locale_code)
    except Locale.DoesNotExist:
        return fallback

    candidates = [page] + list(page.get_ancestors(inclusive=False).order_by("-depth"))
    for candidate in candidates:
        translated = candidate.get_translation_or_none(locale)
        if translated is not None:
            url = translated.get_url(request)
            if url is not None:
                return url

    return fallback
