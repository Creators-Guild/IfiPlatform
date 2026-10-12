"""English slugs: storing them, building /en/ paths from them, and finding
a page by one. The only code that reads or writes the EnglishSlug table.

Hooked into routing and links (route() / get_url_parts()) at the
switch-over; see docs/claude_references/translation_redesign.md.

Design rationale: docs/claude_context/translation_overlay.md"""

from contextlib import contextmanager
from contextvars import ContextVar

from django.utils.text import slugify
from wagtail.models import Page

from ..models.translation import EnglishSlug

_request_memo = ContextVar("english_urls_memo", default=None)


@contextmanager
def request_scope():
    """Inside this block (one request), English slugs and the page tree are
    loaded at most once, so a list of cards doesn't query per link."""
    token = _request_memo.set({})
    try:
        yield
    finally:
        _request_memo.reset(token)


def _remembered(key, load):
    memo = _request_memo.get()
    if memo is None:
        return load()
    if key not in memo:
        memo[key] = load()
    return memo[key]


def _english_slugs():
    """{page id: English slug} for every page that has one."""
    return _remembered(
        "slugs", lambda: dict(EnglishSlug.objects.values_list("page_id", "slug"))
    )


def _tree():
    """{treebeard path: (page id, Norwegian slug)} for every page."""
    return _remembered(
        "tree",
        lambda: {
            path: (pk, slug)
            for path, pk, slug in Page.objects.values_list("path", "pk", "slug")
        },
    )


def english_slug(page):
    """`page`'s English slug, or None if it has none yet."""
    return _english_slugs().get(page.pk)


def path_slug(page_id, norwegian_slug):
    """The slug used in a page's /en/ address: English, else Norwegian."""
    return _english_slugs().get(page_id) or norwegian_slug


def english_url_path(page, site_root):
    """`page`'s path below `site_root` with English slugs, e.g.
    "student-life/freshers-week/". Empty for the root itself."""
    tree, step = _tree(), Page.steplen
    parts = []
    for depth in range(site_root.depth + 1, page.depth + 1):
        pk, slug = tree[page.path[: depth * step]]
        parts.append(path_slug(pk, slug) + "/")
    return "".join(parts)


def find_child(parent, slug):
    """For routing under /en/: (child, by_english). The child of `parent`
    whose English slug is `slug`, else the one whose Norwegian slug is, with
    by_english False (the caller redirects if that child has an English
    slug). (None, False) if neither exists."""
    children = parent.get_children()
    english_ids = [pk for pk, english in _english_slugs().items() if english == slug]
    child = children.filter(pk__in=english_ids).first() if english_ids else None
    if child is not None:
        return child, True
    return children.filter(slug=slug).first(), False


def set_english_slug(page, wanted, source, user=None):
    """Saves `page`'s English slug from `wanted` (any text, slugified), made
    unique among its siblings with -2, -3, ...: never equal to a sibling's
    English slug or Norwegian slug (the fallback address). Returns the slug
    saved."""
    base = slugify(wanted, allow_unicode=True) or page.slug
    siblings = page.get_siblings(inclusive=False)
    taken = set(siblings.values_list("slug", flat=True))
    taken.update(
        EnglishSlug.objects.filter(page__in=siblings).values_list("slug", flat=True)
    )
    slug, number = base, 1
    while slug in taken:
        number += 1
        slug = f"{base}-{number}"
    EnglishSlug.objects.update_or_create(
        page_id=page.pk,
        defaults={"slug": slug, "source": source, "updated_by": user},
    )
    memo = _request_memo.get()
    if memo is not None:
        memo.pop("slugs", None)
    return slug


def set_english_slug_if_missing(page, english_title):
    """Sets the slug once, from the first English title (DeepL). Later title
    changes keep it, so English addresses stay stable."""
    if english_slug(page) is None:
        return set_english_slug(page, english_title, "deepl")
    return None
