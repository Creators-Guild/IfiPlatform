"""Template filters for rendering article body blocks."""

from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """dictionary[key] for templates -- Django's built-in dot lookup only
    works for a literal key written in the template, not a variable, which
    is what looking a block up in block_styles by block.id needs."""
    if dictionary is None:
        return None
    return dictionary.get(str(key))
