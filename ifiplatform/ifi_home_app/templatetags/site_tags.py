"""Template tags for small site-wide content, e.g. the rotating header message."""

from django import template
from django.utils import timezone

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
