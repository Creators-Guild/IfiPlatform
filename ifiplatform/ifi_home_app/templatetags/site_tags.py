"""Template tags for small site-wide content, e.g. the rotating header message."""

from django import template
from django.utils import timezone
from wagtail.models import Locale

from ..models.site_models import HeaderMessage

register = template.Library()


@register.simple_tag
def get_header_message():
    """Return today's header message, cycling through active messages once per day."""
    messages = list(HeaderMessage.objects.filter(is_active=True).order_by("pk"))
    if not messages:
        return None
    index = timezone.now().date().toordinal() % len(messages)
    return messages[index]


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
